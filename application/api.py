from flask import session, current_app as app
from flask_login import login_user
from datetime import timedelta, datetime as dt
import requests
from requests_oauthlib import OAuth2Session
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
from .model_db import db_create, db_read, db_create_or_update_many, db
from .model_db import metric_clean, Insight, Audience, Post, OnlineFollowers, User  # , Campaign
from pprint import pprint

URL = app.config.get('URL')
CAPTURE_BASE_URL = app.config.get('CAPTURE_BASE_URL')
FB_CLIENT_ID = app.config.get('FB_CLIENT_ID')
FB_CLIENT_SECRET = app.config.get('FB_CLIENT_SECRET')
FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
FB_INSPECT_TOKEN_URL = 'https://graph.facebook.com/debug_token'
FB_SCOPE = [
    'pages_show_list',
    'instagram_basic',
    'instagram_manage_insights',
    'manage_pages'
        ]


def generate_app_access_token():
    """ When we need an App access token instead of the app client secret. """
    params = {'client_id': FB_CLIENT_ID, 'client_secret': FB_CLIENT_SECRET}
    params['grant_type'] = 'client_credentials'
    app.logger.info('----------- generate_app_access_token ----------------')
    token = requests.get(FB_AUTHORIZATION_BASE_URL, params=params)
    app.logger.info(token)
    app.logger.info('------------------------------------------------------')
    return token


def inspect_access_token(input_token, fb_id=None, ig_id=None, app_access_token=None):
    """ Confirm the access token is valid and belongs to this user. """
    app_access_token = app_access_token or generate_app_access_token()
    params = {'input_token': input_token, 'access_token': app_access_token}
    res = requests.get(FB_INSPECT_TOKEN_URL, params=params).json()
    if 'error' in res:
        app.logger.info('--------------------- Error in inspect_access_token response ---------------------')
        err = res.get('error', 'Empty Error')
        app.logger.error(f"Error: {err} ")
        return err
    data = res.get('data', {})
    app_match = True if data.get('app_id', 0) == int(FB_CLIENT_ID) else False
    scope_missing = set(FB_SCOPE)
    for ea in data.get('scopes', []):
        scope_missing.remove(ea)
    message = f"Is a Token for our App: {app_match} "
    message += 'Matches FB ID ' if data.get('user_id', '') == fb_id else ''
    message += 'Matches IG ID ' if data.get('user_id', '') == ig_id else ''
    message += f"Missing Scope: {scope_missing} "
    app.logger.info("=============== inspect_access_token ==========================")
    app.logger.info(message)
    pprint(data)
    return data


def user_permissions(user, facebook=None, token=None):
    """ Used by staff to check on what permissions a given user has granted to the platform application. """
    if isinstance(user, (str, int)):
        user = User.query.get(user)
    if not isinstance(user, User):
        app.logger.error("Expected a valid User instance, or id of one, to check what permissions they have granted. ")
        return {}
    if not facebook and not token:
        token = getattr(user, 'token', None)
        if not token:
            app.logger.error("We do not have a token for this user. ")
            return {}
    data = {'id': user.id, 'name': f"{user.name} Permissions Granted"}
    keys = ['facebook_id', 'instagram_id', 'page_id', 'page_token']
    needed = ', '.join([key for key in keys if not getattr(user, key, None)])
    if user.story_subscribed is True:
        subscribed = True
    elif len(needed):
        subscribed = f"False, need {needed} "
    else:
        subscribed = "Have the account and page info, but NOT subscribed. "
    data['subscribed'] = subscribed
    data.update({permission: False for permission in FB_SCOPE})
    url = f"https://graph.facebook.com/{user.facebook_id}/permissions"
    params = {}
    if not facebook:
        params['access_token'] = token
    # TODO: Test facebook.get will work as written below.
    res = facebook.get(url, params=params).json() if facebook else requests.get(url, params=params).json()
    if 'error' in res:
        app.logger.info('--------------------- Error in user_permissions response ---------------------')
        app.logger.error(f"Error: {res.get('error', 'Empty Error')} ")
        return {}
    res_data = res.get('data', [{}])
    data.update({ea.get('permission', ''): ea.get('status', '') for ea in res_data})
    inspect = inspect_access_token(token, fb_id=getattr(user, 'facebook_id'), ig_id=getattr(user, 'instagram_id'))
    if inspect:
        app.logger.info('Got an inspect response. ')
    return data


def capture_media(post_or_posts, get_story_only):
    """ DEPRECATED.
        For a given Post or list of Post objects, call the API for capturing the images of that InstaGram page.
        If get_story_only is True, then only process the Posts that have media_type equal to 'STORY'.
    """
    #  API URL format:
    #  /api/v1/post/
    if isinstance(post_or_posts, Post):
        posts = [post_or_posts]
        started_with_many = False
    elif isinstance(post_or_posts, (list, tuple)):
        posts = post_or_posts
        started_with_many = True
    else:
        raise TypeError("Input must be a Post or an iterable of Posts. ")
    results = []
    for post in posts:
        if not isinstance(post, Post):
            raise TypeError("Every element must be a Post object. ")
        if get_story_only and post.media_type != 'STORY':
            continue  # Skip this one if we are skipping non-story posts.
        # TODO: The following is out of date with the Capture API. Updated code needed if this function is maintained.
        payload = {'url': post.permalink}
        url = f"{CAPTURE_BASE_URL}/api/v1/post/{str(post.id)}/{post.media_type.lower()}/{str(post.media_id)}/"
        try:
            res = requests.get(url, params=payload)
        except Exception as e:
            app.logger.debug("-------- Exception on calling the capture API ----------")
            app.logger.error(e)
            continue
        answer = res.json()
        app.logger.debug(answer)
        if answer.get('success'):
            post.saved_media = answer.get('url_list')
            db.session.add(post)
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
    for insight_metrics, last in [(Insight.INFLUENCE_METRICS, influence_last), (Insight.PROFILE_METRICS, profile_last)]:
        metric = ','.join(insight_metrics)
        for i in range(first, last + 2 - 30, 30):
            until = now - timedelta(days=i)
            since = until - timedelta(days=30)
            url = "https://graph.facebook.com"
            url += f"/{ig_id}/insights?metric={metric}&period={ig_period}&since={since}&until={until}"
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
    metric = ','.join(OnlineFollowers.METRICS)
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
    audience_metric = ','.join(Audience.METRICS)
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
    for name in Audience.IG_DATA:  # {'media_count', 'followers_count'}
        temp = {}
        value = ig_info.get(name, None)
        if value:
            temp['name'] = name
            temp['values'] = [value]
            results.append(temp)
    return db_create_or_update_many(results, user_id=user_id, Model=Audience)


def get_basic_post(media_id, metrics=None, user_id=None, facebook=None, token=None):
    """ Typically called by _get_posts_data_of_user, but also if we have a new Story Post while processing hooks. """
    empty_res = {'media_id': media_id, 'user_id': user_id, 'timestamp': str(dt.utcnow())}
    if not facebook and not token:
        if not user_id:
            message = f"The get_basic_post must have at least one of 'user_id', 'facebook', or 'token' values. "
            app.logger.debug(message)
            raise Exception(message)
        user = User.query.get(user_id)
        token = getattr(user, 'token', None)
        if not token:
            message = f"Unable to locate user token value. User should login with Facebook and authorize permissions. "
            return empty_res
    if not metrics:
        metrics = ','.join(Post.METRICS.get('basic'))
    url = f"https://graph.facebook.com/{media_id}?fields={metrics}"
    try:
        res = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
    except Exception as e:
        auth = 'facebook' if facebook else 'token' if token else 'none'
        app.logger.debug(f"API fail for Post with media_id {media_id} | Auth: {auth} ")
        app.logger.info(e)
        return empty_res
    if 'error' in res:
        # app.logger.error(f"Error: {res.get('error', 'Empty Error')} ")
        app.logger.info('--------------------- Error in get_basic_post FB API response ---------------------')
        # pprint(res)
        return empty_res
    res['media_id'] = res.pop('id', media_id)
    if user_id:
        res['user_id'] = user_id
    return res


def _get_posts_data_of_user(user_id, ig_id=None, facebook=None):
    """ Called by get_posts. Returns the API response data for posts on a single user. """
    user, token = None, None
    if isinstance(user_id, User):
        user = user_id
        user_id = user.id
    if isinstance(user_id, (int, str)):
        pass
    else:
        raise TypeError(f"Expected an id or instance of User, but got {type({user_id})}: {user_id} ")
    if not facebook or not ig_id:
        user = user or User.query.get(user_id)
        ig_id, token = getattr(user, 'instagram_id', None), getattr(user, 'token', None)
    app.logger.info(f"==================== Get Posts on User {user_id} ====================")
    url = f"https://graph.facebook.com/{ig_id}/stories"
    story_res = facebook.get(url).json() if facebook else requests.get(f"{url}?access_token={token}").json()
    stories = story_res.get('data')
    if not isinstance(stories, list) or 'error' in story_res:
        app.logger.error('Error: ', story_res.get('error', 'NA'))
        return []
    story_ids = set([ea.get('id') for ea in stories])
    url = f"https://graph.facebook.com/{ig_id}/media"
    response = facebook.get(url).json() if facebook else requests.get(f"{url}?access_token={token}").json()
    media = response.get('data')
    if not isinstance(media, list):
        app.logger.error('Error: ', response.get('error', 'NA'))
        return []
    media.extend(stories)
    app.logger.info(f"------ Looking up a total of {len(media)} Media Posts, including {len(stories)} Stories ------")
    post_metrics = {key: ','.join(val) for (key, val) in Post.METRICS.items()}
    results = []
    for post in media:
        media_id = post.get('id')
        res = get_basic_post(media_id, metrics=post_metrics['basic'], user_id=user_id, facebook=facebook, token=token)
        media_type = 'STORY' if media_id in story_ids else res.get('media_type')
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
            app.logger.info(f"media {media_id} had NO INSIGHTS for type {media_type} --- {res_insight}. ")
        results.append(res)
    return results


def get_posts(id_or_users, ig_id=None, facebook=None):
    """ Input is a single entity or list of User instance(s), or User id(s).
        Calls the API to get all of the Posts (with insights of Posts) of User(s).
        Saves this data to the Database, creating or updating as needed.
        Returns an array of the saved Post instances.
    """
    if not isinstance(id_or_users, (list, tuple)):
        id_or_users = [id_or_users]
    results = []
    for ea in id_or_users:
        results.extend(_get_posts_data_of_user(ea, ig_id=ig_id, facebook=facebook))
    saved = db_create_or_update_many(results, Post)
    # If any STORY posts were found, the SQLAlchemy Event Listener will add it to the Task queue for the Capture API.
    return saved


def get_fb_page_for_user(user, ignore_current=False, facebook=None, token=None):
    """ For a user with a known Instagram account, we can determine the related Facebook page. """
    if not isinstance(user, User):
        raise Exception(f"get_fb_page_for_user requires a User model instance as the first parameter. ")
    page = dict(zip(['id', 'token'], [getattr(user, 'page_id', None), getattr(user, 'page_token', None)]))
    if ignore_current or not page.get('id') or not page.get('token'):
        ig_id = int(getattr(user, 'instagram_id', 0))
        fb_id = getattr(user, 'facebook_id', 0)
        if not ig_id or not fb_id:
            message = f"We can only get a users page if we already know their accounts on Facebook and Instagram. "
            app.logger.error(message)
            return None
        if not facebook and not token:
            token = getattr(user, 'token', None)
            if not token:
                message = f"We do not have the permission token for this user: {user} "
                app.logger.error(message)
                return None
        url = f"https://graph.facebook.com/{fb_id}"
        app.logger.info(f"========== get_fb_page_for_user {user} ==========")
        params = {'fields': 'accounts'}
        if not facebook:
            params['access_token'] = token
        # TODO: Test facebook.post will work as written below.
        res = facebook.post(url, params=params).json() if facebook else requests.post(url, params=params).json()
        pprint(res)
        accounts = res.pop('accounts', None)
        ig_list = find_instagram_id(accounts, facebook=facebook, token=token)
        matching_ig = [ig_info for ig_info in ig_list if int(ig_info.get('id', 0)) == ig_id]
        ig_info = matching_ig[0] if len(matching_ig) == 1 else {}
        page = {'id': ig_info.get('page_id'), 'token': ig_info.get('page_token'), 'new_page': True}
    success = True if page['id'] and page['token'] else False
    return page if success else None


def install_app_on_user_for_story_updates(user_or_id, page=None, facebook=None, token=None):
    """ Accurate Story Post metrics can be pushed to the Platform only if the App is installed on the related Page. """
    if isinstance(user_or_id, User):
        user = user_or_id
        user_id = user.id
    elif isinstance(user_or_id, (int, str)):
        user_id = int(user_or_id)
        user = User.query.get(user_id)
    else:
        raise ValueError('Input must be either a User model or an id for a User. ')
    app.logger.info(f"========== install_app_on_user_for_story_updates: {user} ==========")
    if not isinstance(page, dict) or not page.get('id') or not page.get('token'):
        page = get_fb_page_for_user(user, facebook=facebook, token=token)
        if not page:
            app.logger.error(f"Unable to find the page for user: {user} ")
            return False
    url = f"https://graph.facebook.com/v3.1/{page['id']}/subscribed_apps"
    params = {} if facebook else {'access_token': page['token']}
    params['subscribed_fields'] = 'name'
    res = facebook.post(url, params=params).json() if facebook else requests.post(url, params=params).json()
    # TODO: See if facebook with params above works.
    app.logger.info('----------------------------------------------------------------')
    pprint(res)
    return res.get('success', False)


def get_ig_info(ig_id, facebook=None, token=None):
    """ We already have their InstaGram Business Account id, but we need their IG username """
    # Possible fields. Fields with asterisk (*) are public and can be returned by and edge using field expansion:
    # biography*, id*, ig_id, followers_count*, follows_count, media_count*, name,
    # profile_picture_url, username*, website*
    fields = ','.join(['username', *Audience.IG_DATA])
    app.logger.info('============ Get IG Info ===================')
    if not token and not facebook:
        logstring = "You must pass a 'token' or 'facebook' reference. "
        app.logger.error(logstring)
        raise ValueError(logstring)
    url = f"https://graph.facebook.com/v4.0/{ig_id}?fields={fields}"
    res = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
    end_time = dt.utcnow().isoformat(timespec='seconds') + '+0000'
    for name in Audience.IG_DATA:
        res[name] = {'end_time': end_time, 'value': res.get(name)}
    return res


def find_instagram_id(accounts, facebook=None, token=None):
    """ For an influencer or brand, we can discover all of their instagram business accounts they have.
        This depends on them having their expected associated facebook page (for each).
    """
    if not facebook and not token:
        message = f"This function requires at least one value for either 'facebook' or 'token' keyword arguments. "
        app.logger.error(message)
        raise Exception(message)
    if not accounts or 'data' not in accounts:
        message = f"No pages found from accounts data: {accounts}. "
        app.logger.info(message)
        return []
    ig_list = []
    pages = [{'id': page.get('id'), 'token': page.get('access_token')} for page in accounts.get('data')]
    app.logger.info(f"============ Pages count: {len(pages)} ============")
    for page in pages:
        url = f"https://graph.facebook.com/v4.0/{page['id']}?fields=instagram_business_account"
        req_token, err = page['token'], 10
        while err > 1:
            res = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={req_token}").json()
            if 'error' in res and res['error'].get('code', 0) in (100, 190):
                if err == 10:
                    err = 100
                    req_token = token
                    app.logger.info("Will try app token for user. ")
                elif err == 100:
                    err = 200
                    app.logger.info("Will try a generated App Token. ")
                    token = generate_app_access_token()
                else:
                    err = 1
            else:
                err = 0
        ig_business = res.get('instagram_business_account', None)
        if ig_business:
            ig_info = get_ig_info(ig_business.get('id', None), facebook=facebook, token=token)
            ig_info['page_id'] = page['id']
            ig_info['page_token'] = page['token']
            ig_list.append(ig_info)
        elif 'error' in res:
            app.logger.error(f"Error on getting info from {page['id']} Page. ")
            pprint(res)
        else:
            app.logger.info("No Appropriate Account on this page. ")
            pprint(res)
    return ig_list


def onboard_login(mod):
    """ Process the initiation of creating a new influencer or brand user with facebook authorization. """
    callback = URL + '/callback/' + mod
    facebook = OAuth2Session(FB_CLIENT_ID, redirect_uri=callback, scope=FB_SCOPE)
    authorization_url, state = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)
    session['oauth_state'] = state
    return authorization_url


def onboarding(mod, request):
    """ Verify the authorization request and create the appropriate influencer or brand user. """
    callback = URL + '/callback/' + mod
    facebook = OAuth2Session(FB_CLIENT_ID, scope=FB_SCOPE, redirect_uri=callback, state=session['oauth_state'])
    facebook = facebook_compliance_fix(facebook)  # we need to apply a fix for Facebook here
    # TODO: ? Modify input parameters to only pass the request.url value since that is all we use?
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
        data['page_id'] = ig_info.get('page_id')
        data['page_token'] = ig_info.get('page_token')
        models = []
        for name in Audience.IG_DATA:  # {'media_count', 'followers_count'}
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
