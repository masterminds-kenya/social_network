from flask import current_app as app
from flask_login import login_user
from .model_db import db_create, db_read, db_create_or_update_many
from .model_db import metric_clean, Insight, Audience, Post, OnlineFollowers, User  # , Campaign
import requests
import requests_oauthlib
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
from datetime import datetime as dt
from datetime import timedelta
# from pprint import pprint

URL = app.config.get('URL')
FB_CLIENT_ID = app.config.get('FB_CLIENT_ID')
FB_CLIENT_SECRET = app.config.get('FB_CLIENT_SECRET')
FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
FB_SCOPE = [
    'pages_show_list',
    'instagram_basic',
    'instagram_manage_insights',
        ]


def get_insight(user_id, first=1, influence_last=30*12, profile_last=30*3, ig_id=None, facebook=None):
    """ Get the insight metrics for the User. """
    ig_period = 'day'
    results, token = [], ''
    if not facebook or not ig_id:
        user = db_read(user_id, safe=False)
        ig_id, token = user.get('instagram_id'), user.get('token')
    # TODO: Query for this user's most recent influence_metric and most recent profile_metric
    # adjust each version of last to not overlap from previous request. Use mod to make it a multiple of 30.
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
    # logstring = f"We have Online Followers data!" if follow_report else "No follow report"
    # app.logger.info(logstring)
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
        app.logger.info(f"Online Followers Error: {response.get('error')}")
        return None
    results = []
    for day in data[0].get('values', []):  # We expect only 1 element in the 'data' list
        end_time = day.get('end_time')
        for hour, val in day.get('value', {}).items():
            results.append({'user_id': user_id, 'hour': int(hour), 'value': int(val), 'end_time': end_time})
    # pprint(results)
    return db_create_or_update_many(results, user_id=user_id, Model=OnlineFollowers)


def get_audience(user_id, ig_id=None, facebook=None):
    """ Get the audience data for the (influencer or brand) user with given user_id """
    app.logger.info('=========================== Get Audience Data ======================')
    audience_metric = ','.join(Audience.metrics)
    app.logger.info(audience_metric)
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
    # pprint(audience.get('data'))
    for ea in audience.get('data'):
        ea['user_id'] = user_id
        results.append(ea)
    return db_create_or_update_many(results, user_id=user_id, Model=Audience)


def get_posts(user_id, ig_id=None, facebook=None):
    """ Get media posts for the (influencer or brand) user with given user_id """
    app.logger.info('==================== Get Posts ====================')
    post_metrics = {key: ','.join(val) for (key, val) in Post.metrics.items()}
    results, token = [], ''
    if not facebook or not ig_id:
        model = db_read(user_id, safe=False)
        ig_id, token = model.get('instagram_id'), model.get('token')
    url = f"https://graph.facebook.com/{ig_id}/stories"
    story_res = facebook.get(url).json() if facebook else requests.get(f"{url}?access_token={token}").json()
    stories = story_res.get('data')
    if not isinstance(stories, list):
        app.logger.error('Error: ', story_res.get('error'))
        return []
    story_ids = {ea.get('id') for ea in stories}
    url = f"https://graph.facebook.com/{ig_id}/media"
    response = facebook.get(url).json() if facebook else requests.get(f"{url}?access_token={token}").json()
    media = response.get('data')
    if not isinstance(media, list):
        app.logger.error('Error: ', response.get('error'))
        return []
    media.extend(stories)
    # print(f"----------- Looking up a total of {len(media)} Media Posts, including {len(stories)} Stories ----------- ")
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
            app.logger.error(f" Match not found for {media_type} media_type parameter ")
        url = f"https://graph.facebook.com/{media_id}/insights?metric={metrics}"
        res_insight = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
        insights = res_insight.get('data')
        if insights:
            temp = {ea.get('name'): ea.get('values', [{'value': 0}])[0].get('value', 0) for ea in insights}
            if media_type == 'CAROUSEL_ALBUM':
                temp = {metric_clean(key): val for key, val in temp.items()}
            res.update(temp)
        else:
            app.logger.info(f"media {media_id} had NO INSIGHTS for type {media_type} --- {res_insight}")
        results.append(res)
    return db_create_or_update_many(results, Post)


def get_ig_info(ig_id, token=None, facebook=None):
    """ We already have their InstaGram Business Account id, but we need their IG username """
    # Possible fields. Fields with asterisk (*) are public and can be returned by and edge using field expansion:
    # biography*, id*, ig_id, followers_count*, follows_count, media_count*, name,
    # profile_picture_url, username*, website*
    fields = ['username', *Audience.ig_data]
    fields = ','.join(fields)
    # print('============ Get IG Info ===================')
    if not token and not facebook:
        logstring = "You must pass a 'token' or 'facebook' reference. "
        app.logger.error(logstring)
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
    if pages:
        app.logger.info(f'============ Pages count: {len(pages)} ============')
        for page in pages:
            instagram_data = facebook.get(f"https://graph.facebook.com/v4.0/{page}?fields=instagram_business_account").json()
            ig_business = instagram_data.get('instagram_business_account', None)
            if ig_business:
                ig_info = get_ig_info(ig_business.get('id', None), facebook=facebook)
                ig_list.append(ig_info)
    return ig_list


def onboard_login(mod):
    """ Process the initiation of creating a new influencer or brand user with facebook authorization. """
    callback = URL + '/callback/' + mod
    facebook = requests_oauthlib.OAuth2Session(
        FB_CLIENT_ID, redirect_uri=callback, scope=FB_SCOPE
    )
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
    # Fetch a protected resources:
    facebook_user_data = facebook.get("https://graph.facebook.com/me?fields=id,accounts").json()
    if 'error' in facebook_user_data:
        return ('error', facebook_user_data, None)
    # TODO: use a better constructor for the user account.
    data = facebook_user_data.copy()  # .to_dict(flat=True)
    data['role'] = mod
    data['token'] = token
    accounts = data.pop('accounts')
    # Collect IG usernames for all options
    ig_list = find_instagram_id(accounts, facebook=facebook)
    # If they only have 1 ig account, assign the appropriate instagram_id
    ig_id = None
    if len(ig_list) == 100:
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
        app.logger.info('------ Only 1 InstaGram business account ------')
    else:
        data['name'] = data.get('username', None) if 'name' not in data else data['name']
        app.logger.info(f'------ Found {len(ig_list)} potential IG accounts ------')
    # app.logger.info('=========== Data sent to Create User account ===============')
    # pprint(data)
    # TODO: Create and use a User method that will create or use existing User, and returns a User object.
    # Refactor next three lines to utilize this method so we are just dealing with the User object.
    account = db_create(data)
    account_id = account.get('id')
    login_user(User.query.get(account_id), force=True, remember=True)
    app.logger.info(f"New {mod} User: {account_id}")
    if ig_id:
        # Relate Data
        insights = get_insight(account_id, ig_id=ig_id, facebook=facebook)
        print('We have IG account insights') if insights else print('No IG account insights')
        audience = get_audience(account_id, ig_id=ig_id, facebook=facebook)
        print('Audience data collected') if audience else print('No Audience data')
        return ('complete', 0, account_id)
    else:
        # Allow this Facebook account to select one of many of their IG business accounts
        return ('decide', ig_list, account_id)
