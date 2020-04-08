from flask import current_app as app
from flask_login import login_user
from .model_db import db_create, db_read, db_create_or_update_many, db
from .model_db import metric_clean, Insight, Audience, Post, OnlineFollowers, User  # , Campaign
import requests
import requests_oauthlib
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
from datetime import datetime as dt
from datetime import timedelta
from pprint import pprint

URL = app.config.get('URL')
CAPTURE_BASE_URL = app.config.get('CAPTURE_BASE_URL')
FB_CLIENT_ID = app.config.get('FB_CLIENT_ID')
FB_CLIENT_SECRET = app.config.get('FB_CLIENT_SECRET')
FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
FB_SCOPE = [
    'pages_show_list',
    'instagram_basic',
    'instagram_manage_insights',
    'manage_pages'
        ]


def capture_media(post_or_posts, get_story_only):
    """ For a given Post or list of Post objects, call the API for capturing the images of that InstaGram page.
        If get_story_only is True, then only process the Posts that have media_type equal to 'STORY'.
    """
    #  API URL format:
    #  /api/v1/post/[id]/[media_type]/[media_id]/?url=[url-to-test-for-images]
    #  Expected JSON response has the following properties:
    #  'success', 'message', 'file_list', 'url', 'url_list', 'error_files', 'deleted'
    started_with_many = True
    if isinstance(post_or_posts, Post):
        posts = [post_or_posts]
        started_with_many = False
    elif isinstance(post_or_posts, (list, tuple)):
        posts = post_or_posts
    else:
        raise TypeError("Input must be a Post or an iterable of Posts. ")
    results = []
    for post in posts:
        if not isinstance(post, Post):
            raise TypeError("Every element must be a Post object. ")
        if get_story_only and post.media_type != 'STORY':
            continue  # Skip this one if we are skipping non-story posts.
        payload = {'url': post.permalink}
        url = f"{CAPTURE_BASE_URL}/api/v1/post/{str(post.id)}/{post.media_type.lower()}/{str(post.media_id)}/"
        app.logger.debug('--------- Capture Media Url -------------')
        app.logger.debug(url)
        try:
            res = requests.get(url, params=payload)
        except Exception as e:
            app.logger.debug("-------- Exception on calling the capture API ----------")
            app.logger.error(e)
            continue
        answer = res.json()
        app.logger.debug(answer)
        if answer.get('success'):
            post.saved_media = answer.get('url')
            answer['saved_media'] = True
        else:
            answer['saved_media'] = False
        answer['post_model'] = post
        results.append(answer)
    if results:
        db.session.commit()
    else:
        message = "Started with no Posts. " if not posts else "No story Posts. " if get_story_only else "Error. "
        answer = {'success': True, 'message': message, 'url': ''}
        for key in ['file_list', 'url_list', 'error_files', 'deleted']:
            answer[key] = []
        results.append(answer)
    return results if started_with_many else results[0]


def get_insight(user_id, first=1, influence_last=30*12, profile_last=30*3, ig_id=None, facebook=None):
    """ Get the insight metrics for the User. Has default values, but can be called with custom durations.
        It will check existing data to see how recently we have insight metrics for this user.
        It will request results for the full duration, or since recent data, or a minimum of 30 days.
    """
    ig_period = 'day'
    results, token = [], ''
    user = User.query.get(user_id)
    if not facebook or not ig_id:
        ig_id, token = getattr(user, 'instagram_id', None), getattr(user, 'token', None)
    now = dt.utcnow()
    influence_date = user.recent_insight('influence')
    profile_date = user.recent_insight('profile')
    if influence_date:
        influence_last = max(30, int(min(influence_last, (now - influence_date).days)))
        app.logger.debug("Updated Influence Last. ")
    if profile_date:
        profile_last = max(30, int(min(profile_last, (now - profile_date).days)))
        app.logger.debug('Updated Profile Last')
    app.logger.info("------------ Get Insight: Influence, Profile ---------------")
    app.logger.debug(influence_last)
    app.logger.debug(profile_last)
    for insight_metrics, last in [(Insight.influence_metrics, influence_last), (Insight.profile_metrics, profile_last)]:
        metric = ','.join(insight_metrics)
        for i in range(first, last + 2 - 30, 30):
            until = dt.utcnow() - timedelta(days=i)
            since = until - timedelta(days=30)
            url = f"https://graph.facebook.com/{ig_id}/insights?metric={metric}&period={ig_period}&since={since}&until={until}"
            response = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
            insights = response.get('data')
            if not insights:
                app.logger.error('Error: ', response.get('error'))
                return None
            for ea in insights:
                for val in ea.get('values'):
                    val['name'], val['user_id'] = ea.get('name'), user_id
                    results.append(val)
    models = db_create_or_update_many(results, user_id=user_id, Model=Insight)
    follow_report = get_online_followers(user_id, ig_id=ig_id, facebook=facebook)
    logstring = f"Added Online Followers data. " if follow_report else "No follow report. "
    app.logger.debug(logstring)
    return (models, follow_report)


def get_online_followers(user_id, ig_id=None, facebook=None):
    """ Just want to get Facebook API response for online_followers for the maximum of the previous 30 days """
    app.logger.info('================= Get Online Followers data ==============')
    ig_period, token = 'lifetime', ''
    metric = ','.join(OnlineFollowers.metrics)
    if not facebook or not ig_id:
        model = db_read(user_id, safe=False)
        ig_id, token = model.get('instagram_id'), model.get('token')
    until = dt.utcnow() - timedelta(days=1)
    since = until - timedelta(days=30)
    url = f"https://graph.facebook.com/{ig_id}/insights?metric={metric}&period={ig_period}&since={since}&until={until}"
    response = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
    data = response.get('data')
    if not data:
        app.logger.error(f"Online Followers Error: {response.get('error')}. ")
        return None
    results = []
    for day in data[0].get('values', []):  # We expect only 1 element in the 'data' list
        end_time = day.get('end_time')
        for hour, val in day.get('value', {}).items():
            results.append({'user_id': user_id, 'hour': int(hour), 'value': int(val), 'end_time': end_time})
    return db_create_or_update_many(results, user_id=user_id, Model=OnlineFollowers)


def get_audience(user_id, ig_id=None, facebook=None):
    """ Get the audience data for the (influencer or brand) user with given user_id """
    app.logger.info('=========================== Get Audience Data ======================')
    audience_metric = ','.join(Audience.metrics)
    ig_period = 'lifetime'
    results, token = [], ''
    if not facebook or not ig_id:
        model = db_read(user_id, safe=False)
        ig_id, token = model.get('instagram_id'), model.get('token')
    url = f"https://graph.facebook.com/{ig_id}/insights?metric={audience_metric}&period={ig_period}"
    audience = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
    if not audience.get('data'):
        app.logger.error(f"Error: {audience.get('error')}")
        return None
    for ea in audience.get('data'):
        ea['user_id'] = user_id
        results.append(ea)
    ig_info = get_ig_info(ig_id, token=token, facebook=facebook)
    for name in Audience.ig_data:  # {'media_count', 'followers_count'}
        temp = {}
        value = ig_info.get(name, None)
        if value:
            temp['name'] = name
            temp['values'] = [value]
            results.append(temp)
    return db_create_or_update_many(results, user_id=user_id, Model=Audience)


def get_posts(user_id, ig_id=None, facebook=None):
    """ Get media posts (including stories) for the (influencer or brand) user with given user_id """
    app.logger.info('==================== Get Posts ====================')
    post_metrics = {key: ','.join(val) for (key, val) in Post.metrics.items()}
    results, token = [], ''
    if not facebook or not ig_id:
        model = db_read(user_id, safe=False)
        ig_id, token = model.get('instagram_id'), model.get('token')
    url = f"https://graph.facebook.com/{ig_id}/stories"
    story_res = facebook.get(url).json() if facebook else requests.get(f"{url}?access_token={token}").json()
    stories = story_res.get('data')
    if not isinstance(stories, list) and 'error' in story_res:
        app.logger.error('Error: ', story_res.get('error', 'NA'))
        return []
    story_ids = [ea.get('id') for ea in stories]
    url = f"https://graph.facebook.com/{ig_id}/media"
    response = facebook.get(url).json() if facebook else requests.get(f"{url}?access_token={token}").json()
    media = response.get('data')
    if not isinstance(media, list):
        app.logger.error('Error: ', response.get('error', 'NA'))
        return []
    media.extend(stories)
    app.logger.debug(f"------- Looking up a total of {len(media)} Media Posts, including {len(stories)} Stories -------")
    for post in media:
        media_id = post.get('id')
        url = f"https://graph.facebook.com/{media_id}?fields={post_metrics['basic']}"
        res = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
        res['media_id'] = res.pop('id', media_id)
        res['user_id'] = user_id
        media_type = 'STORY' if res['media_id'] in story_ids else res.get('media_type')
        res['media_type'] = media_type
        metrics = post_metrics.get(media_type, post_metrics['insight'])
        if metrics == post_metrics['insight']:
            app.logger.error(f" Match not found for {media_type} media_type parameter. ")
        url = f"https://graph.facebook.com/{media_id}/insights?metric={metrics}"
        res_insight = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
        insights = res_insight.get('data')
        if insights:
            temp = {ea.get('name'): ea.get('values', [{'value': 0}])[0].get('value', 0) for ea in insights}
            if media_type == 'CAROUSEL_ALBUM':
                temp = {metric_clean(key): val for key, val in temp.items()}
            res.update(temp)
        else:
            app.logger.debug(f"media {media_id} had NO INSIGHTS for type {media_type} --- {res_insight}. ")
        results.append(res)
    saved = db_create_or_update_many(results, Post)
    # TODO: URGENT Capture Media for all stories in saved.
    # captured = [capture_media(ea) for ea in saved if ea.get('media_id') in story_ids]
    capture_responses = capture_media(saved, True)
    failed_capture = [ea.get('post') for ea in capture_responses if not ea.get('saved_media')]
    message = f"Had {len(capture_responses)} story posts. "
    message += f"Had {len(failed_capture)} failed media captures. " if failed_capture else "All media captured. "
    app.logger.info(message)
    app.logger.info(failed_capture)
    return saved


def get_ig_info(ig_id, token=None, facebook=None):
    """ We already have their InstaGram Business Account id, but we need their IG username """
    # Possible fields. Fields with asterisk (*) are public and can be returned by and edge using field expansion:
    # biography*, id*, ig_id, followers_count*, follows_count, media_count*, name,
    # profile_picture_url, username*, website*
    fields = ['username', *Audience.ig_data]
    fields = ','.join(fields)
    app.logger.info('============ Get IG Info ===================')
    if not token and not facebook:
        logstring = "You must pass a 'token' or 'facebook' reference. "
        app.logger.error(logstring)
        # TODO: Raise error and handle raised error where this function is called.
        return logstring
    url = f"https://graph.facebook.com/v4.0/{ig_id}?fields={fields}"
    res = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
    end_time = dt.utcnow().isoformat(timespec='seconds') + '+0000'
    for name in Audience.ig_data:
        res[name] = {'end_time': end_time, 'value': res.get(name)}
    return res


def find_instagram_id(accounts, facebook=None):
    """ For an influencer or brand, we can discover all of their instagram business accounts they have.
        This depends on them having their expected associated facebook page (for each).
    """
    ig_list = []
    pages = [page.get('id') for page in accounts.get('data')] if accounts and 'data' in accounts else None
    if not facebook:
        app.logger.error("The parameter for facebook can not be None. ")
    if pages:
        app.logger.debug(f"============ Pages count: {len(pages)} ============")
        for page in pages:
            instagram_data = facebook.get(f"https://graph.facebook.com/v4.0/{page}?fields=instagram_business_account").json()
            if 'error' in instagram_data:
                app.logger.error(f"Error on getting info from {page} Page. ")
                pprint(instagram_data)
            ig_business = instagram_data.get('instagram_business_account', None)
            if ig_business:
                ig_info = get_ig_info(ig_business.get('id', None), facebook=facebook)
                ig_list.append(ig_info)
    else:
        app.logger.error(f"No pages found from accounts data: {accounts}. ")
    return ig_list


def onboard_login(mod):
    """ Process the initiation of creating a new influencer or brand user with facebook authorization. """
    callback = URL + '/callback/' + mod
    facebook = requests_oauthlib.OAuth2Session(FB_CLIENT_ID, redirect_uri=callback, scope=FB_SCOPE)
    authorization_url, state = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)
    # session['oauth_state'] = state
    return authorization_url


def onboarding(mod, request):
    """ Verify the authorization request and create the appropriate influencer or brand user. """
    callback = URL + '/callback/' + mod
    facebook = requests_oauthlib.OAuth2Session(FB_CLIENT_ID, scope=FB_SCOPE, redirect_uri=callback)
    facebook = facebook_compliance_fix(facebook)  # we need to apply a fix for Facebook here
    token = facebook.fetch_token(FB_TOKEN_URL, client_secret=FB_CLIENT_SECRET, authorization_response=request.url)
    if 'error' in token:
        return ('error', token, None)
    facebook_user_data = facebook.get("https://graph.facebook.com/me?fields=id,accounts").json()
    if 'error' in facebook_user_data:
        return ('error', facebook_user_data, None)
    # TODO: use a better constructor for the user account.
    data = facebook_user_data.copy()  # .to_dict(flat=True)
    data['role'] = mod
    data['token'] = token
    accounts = data.pop('accounts', None)
    ig_list = find_instagram_id(accounts, facebook=facebook)
    ig_id = None
    if len(ig_list) == 1:
        ig_info = ig_list.pop()
        data['name'] = ig_info.get('username', None)
        ig_id = int(ig_info.get('id'))
        data['instagram_id'] = ig_id
        models = []
        for name in Audience.ig_data:  # {'media_count', 'followers_count'}
            value = ig_info.get(name, None)
            if value:
                models.append(Audience(name=name, values=[value]))
        data['audiences'] = models
        app.logger.debug('------ Only 1 InstaGram business account ------')
    else:
        data['name'] = data.get('id', None) if 'name' not in data else data['name']
        app.logger.debug(f'------ Found {len(ig_list)} potential IG accounts ------')
    # TODO: Create and use a User method that will create or use existing User, and returns a User object.
    # Refactor next three lines to utilize this method so we don't need the extra query based on id.
    account = db_create(data)
    account_id = account.get('id')
    user = User.query.get(account_id)
    login_user(user, force=True, remember=True)
    if ig_id:
        insights, follow_report = get_insight(account_id, ig_id=ig_id, facebook=facebook)
        message = "We have IG account insights. " if insights else "No IG account insights. "
        message += "We have IG followers report. " if follow_report else "No IG followers report. "
        audience = get_audience(account_id, ig_id=ig_id, facebook=facebook)
        message += "Audience data collected. " if audience else "No Audience data. "
        app.logger.info(message)
        return ('complete', 0, account_id)
    else:  # This Facebook user needs to select one of many of their IG business accounts
        return ('decide', ig_list, account_id)
