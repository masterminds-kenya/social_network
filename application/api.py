from . import model_db
import requests
import requests_oauthlib
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
from os import environ
from datetime import datetime as dt
from datetime import timedelta
import re
from pprint import pprint

FB_CLIENT_ID = environ.get('FB_CLIENT_ID')
FB_CLIENT_SECRET = environ.get('FB_CLIENT_SECRET')
FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
FB_SCOPE = [
    'pages_show_list',
    'instagram_basic',
    'instagram_manage_insights',
        ]


def get_insight(user_id, first=1, last=30*3, ig_id=None, facebook=None):
    """ Practice getting some insight data with the provided facebook oauth session """
    ig_period = 'day'
    results, token = [], ''
    insight_metric = ','.join(model_db.Insight.metrics)
    if not facebook or not ig_id:
        model = model_db.read(user_id, safe=False)
        ig_id, token = model.get('instagram_id'), model.get('token')
    for i in range(first, last + 2 - 30, 30):
        until = dt.utcnow() - timedelta(days=i)
        since = until - timedelta(days=30)
        url = f"https://graph.facebook.com/{ig_id}/insights?metric={insight_metric}&period={ig_period}&since={since}&until={until}"
        response = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
        test_insights = response.get('data')
        if not test_insights:
            print('Error: ', response.get('error'))
            return None
        for ea in test_insights:
            for val in ea.get('values'):
                val['name'], val['user_id'] = ea.get('name'), user_id
                results.append(val)
    return model_db.create_or_update_many(results, user_id=user_id, Model=model_db.Insight)


def get_audience(user_id, ig_id=None, facebook=None):
    """ Get the audience data for the user of user_id """
    print('=========================== Get Audience Data ======================')
    audience_metric = ','.join(model_db.Audience.metrics)
    ig_period = 'lifetime'
    results, token = [], ''
    if not facebook or not ig_id:
        model = model_db.read(user_id, safe=False)
        ig_id, token = model.get('instagram_id'), model.get('token')
    url = f"https://graph.facebook.com/{ig_id}/insights?metric={audience_metric}&period={ig_period}"
    audience = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
    for ea in audience.get('data'):
        ea['user_id'] = user_id
        results.append(ea)
    return model_db.create_or_update_many(results, user_id=user_id, Model=model_db.Audience)


def get_posts(user_id, ig_id=None, facebook=None):
    """ Get media posts """
    print('==================== Get Posts ====================')
    post_metrics = {key: ','.join(val) for (key, val) in model_db.Post.metrics.items()}
    results, token = [], ''
    if not facebook or not ig_id:
        model = model_db.read(user_id, safe=False)
        ig_id, token = model.get('instagram_id'), model.get('token')
    url = f"https://graph.facebook.com/{ig_id}/stories"
    story_res = facebook.get(url).json() if facebook else requests.get(f"{url}?access_token={token}").json()
    stories = story_res.get('data')
    if not isinstance(stories, list):
        print('Error: ', story_res.get('error'))
        print('--------------- something wrong with story posts ----------------')
        pprint(story_res)
        return []
    story_ids = {ea.get('id') for ea in stories}
    url = f"https://graph.facebook.com/{ig_id}/media"
    response = facebook.get(url).json() if facebook else requests.get(f"{url}?access_token={token}").json()
    media = response.get('data')
    if not isinstance(media, list):
        print('Error: ', response.get('error'))
        print('--------------- Something wrong with media posts ----------------')
        pprint(response)
        return []
    media.extend(stories)
    print(f"----------- Looking up a total of {len(media)} Media Posts, including {len(stories)} Stories ----------- ")
    for post in media:
        media_id = post.get('id')
        url = f"https://graph.facebook.com/{media_id}?fields={post_metrics['basic']}"
        res = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
        res['media_id'] = res.pop('id', media_id)
        res['user_id'] = user_id
        media_type = 'STORY' if res['media_id'] in story_ids else res.get('media_type')
        res['media_type'] = media_type
        metrics = post_metrics.get(media_type, post_metrics['insight'])
        if metrics == post_metrics['insight']:  # TODO: remove after tested
            print(f"----- Match not found for {media_type} media_type parameter -----")  # TODO: remove after tested
        url = f"https://graph.facebook.com/{media_id}/insights?metric={metrics}"
        res_insight = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
        insights = res_insight.get('data')
        if insights:
            temp = {ea.get('name'): ea.get('values', [{'value': 0}])[0].get('value', 0) for ea in insights}
            if media_type == 'CAROUSEL_ALBUM':
                temp = {re.sub('^carousel_album_', '', key): val for key, val in temp.items()}
            res.update(temp)
        else:
            print(f"media {media_id} had NO INSIGHTS for type {media_type} --- {res_insight}")
        # pprint(res)
        # print('---------------------------------------')
        results.append(res)
    return model_db.create_or_update_many(results, model_db.Post)


def get_ig_info(ig_id, token=None, facebook=None):
    """ We already have their InstaGram Business Account id, but we need their IG username """
    # Possible fields. Fields with asterisk (*) are public and can be returned by and edge using field expansion:
    # biography*, id*, ig_id, followers_count*, follows_count, media_count*, name,
    # profile_picture_url, username*, website*
    fields = ['username', 'followers_count', 'follows_count', 'media_count']
    fields = ','.join(fields)
    print('============ Get IG Info ===================')
    if not token and not facebook:
        return "You must pass a 'token' or 'facebook' reference. "
    url = f"https://graph.facebook.com/v4.0/{ig_id}?fields={fields}"
    res = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
    pprint(res)
    return res


def find_instagram_id(accounts, facebook=None):
    ig_list = []
    pages = [page.get('id') for page in accounts.get('data')] if accounts and 'data' in accounts else None
    # TODO: Update logic for user w/ many pages/instagram-accounts. Currently assumes last found instagram account
    if pages:
        print(f'================= Pages count: {len(pages)} =================================')
        for page in pages:
            instagram_data = facebook.get(f"https://graph.facebook.com/v4.0/{page}?fields=instagram_business_account").json()
            ig_business = instagram_data.get('instagram_business_account', None)
            if ig_business:
                ig_info = get_ig_info(ig_business.get('id', None), facebook=facebook)
                ig_list.append(ig_info)
    return ig_list


def onboard_login(URL):
    callback = URL + '/callback'
    facebook = requests_oauthlib.OAuth2Session(
        FB_CLIENT_ID, redirect_uri=callback, scope=FB_SCOPE
    )
    authorization_url, state = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)
    # session['oauth_state'] = state
    return authorization_url


def onboarding(URL, request):
    callback = URL + '/callback'
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
    data['token'] = token
    accounts = data.pop('accounts')
    # Collect IG usernames for all options
    ig_list = find_instagram_id(accounts, facebook=facebook)
    # If they only have 1 ig account, continue making things
    ig_id = None
    if len(ig_list) == 1:
        ig_info = ig_list.pop()
        data['name'] = ig_info.get('username', None)
        ig_id = ig_info.get('id')
        data['instagram_id'] = ig_id
        print('------ Only 1 InstaGram business account --------')
    else:
        data['name'] = data.get('username', None) if 'name' not in data else data['name']
        print(f'--------- Found {len(ig_list)} potential IG accounts -----------')
    print('=================== Data sent to Create User =======================')
    pprint(data)
    user = model_db.create(data)
    user_id = user.get('id')
    print('User: ', user_id)
    if ig_id:
        # Relate Data
        insights = get_insight(user_id, last=90, ig_id=ig_id, facebook=facebook)
        print('We have IG account insights') if insights else print('No IG account insights')
        audience = get_audience(user_id, ig_id=ig_id, facebook=facebook)
        print('Audience data collected') if audience else print('No Audience data')
        return ('complete', 0, user_id)
    else:
        # Allow this Facebook user to select one of many of their IG business accounts
        # TODO: The following 'mod' needs to be updated if this function is used for Brand Model
        return ('decide', ig_list, user_id)
