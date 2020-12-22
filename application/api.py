from flask import session, current_app as app
# from flask_sqlalchemy import BaseQuery
# from sqlalchemy.orm import load_only
from flask_login import login_user, logout_user, current_user
from datetime import timedelta  # , datetime as dt
import requests
from requests_oauthlib import OAuth2Session  # , BackendApplicationClient
# from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
from .model_db import translate_api_user_token, db_create, db_create_or_update_many, db  # , db_read,
from .model_db import metric_clean, Insight, Audience, Post, OnlineFollowers, User  # , Campaign
from .helper_functions import make_missing_timestamp
from pprint import pprint

URL = app.config.get('URL')
CAPTURE_BASE_URL = app.config.get('CAPTURE_BASE_URL')
FB_CLIENT_APP_NAME = app.config.get('FB_CLIENT_APP_NAME', 'Bacchus Influencer Platform')
FB_CLIENT_ID = app.config.get('FB_CLIENT_ID')
FB_CLIENT_SECRET = app.config.get('FB_CLIENT_SECRET')
FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
# GRAPH_URL = "https://graph.facebook.com/"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
FB_INSPECT_TOKEN_URL = 'https://graph.facebook.com/debug_token'
FB_SCOPE = [
    'pages_show_list',
    'pages_read_engagement',  # Graph API v7.0 requires this to get instagram_basic permissions.
    'instagram_basic',
    'instagram_manage_insights',
    'pages_manage_metadata',
    # 'manage_pages'  # Deprecated. Now using pages_read_engagement (v7.0), 'pages_manage_metadata' for later.
    ]
# TODO: Implement request of permissions previously rejected: The FB_AUTHORIZATION_BASE_URL with auth_type=rerequest
METRICS = {
    OnlineFollowers: ','.join(OnlineFollowers.METRICS),
    Audience: ','.join(Audience.METRICS),
    Insight: {'influence': ','.join(Insight.INFLUENCE_METRICS), 'profile': ','.join(Insight.PROFILE_METRICS)},
    Post: {key: ','.join(val) for key, val in Post.METRICS.items()},
    # Keys in Post: basic, insight, IMAGE, VIDEO, CAROUSEL_ALBUM, STORY
    }

# TODO: CRITICAL All API calls need to handle pagination results.


def find_valid_user(id_or_user, instagram_required=True, token_required=True):
    """For a given user with a saved token, create an OAuth2Session for Graph API requests of their data. """
    if isinstance(id_or_user, User):
        user = id_or_user
    elif isinstance(id_or_user, (int, str)):
        user_id = int(id_or_user)
        user = User.query.get(user_id)  # If not a valid id, expect a return of None.
    else:
        # if not isinstance(id_or_user, BaseQuery):
        raise TypeError(f"Expected an id or instance of User, but got {type({id_or_user})}: {id_or_user} ")
        # else:
        #     opts = []
        #     if instagram_required:
        #         opts.append(User.instagram_id.isnot(None))
        #     if token_required:
        #         opts.append(User.token.isnot(None))
        #     q = id_or_user.filter(*opts)
        #     return q.all()
    if instagram_required and not user.instagram_id:
        user = None
    if token_required and not user.token:
        user = None
    return user

# def generate_backend_token():
#     """When an App access token (as proof the request is from BIP App) is needed instead of the app client secret. """
#     client = BackendApplicationClient(client_id=FB_CLIENT_ID)
#     oauth = OAuth2Session(client=client)
#     token = oauth.fetch_token(token_url=FB_TOKEN_URL, client_id=FB_CLIENT_ID, client_secret=FB_CLIENT_SECRET)
#     # What about the params['grant_type'] = 'client_credentials' in generate_app_access_token ?
#     # token = token.get('access_token')  ??
#     return token


def generate_app_access_token():
    """When an App access token (as proof the request is from BIP App) is needed instead of the app client secret. """
    params = {'client_id': FB_CLIENT_ID, 'client_secret': FB_CLIENT_SECRET}
    params['grant_type'] = 'client_credentials'
    app.logger.info('----------- generate_app_access_token ----------------')
    res = requests.get(FB_TOKEN_URL, params=params).json()
    if 'error' in res:
        app.logger.info('Got an error in generate_app_access_token')
        app.logger.error(res.get('error', 'Empty Error'))
    token = res.get('access_token', '')
    return token


def pretty_token_data(data, fb_id=None, ig_id=None, page_id=None, **kwargs):
    """Takes the response from 'inspect_access_token' and adds useful key:values for reports. """
    data = data.copy()  # TODO: Check if it should be a deepcopy?
    val_name_pairs = zip((fb_id, ig_id, page_id), ('facebook_id', 'instagram_id', 'page_id'))
    known_ids = {int(k): v for k, v in val_name_pairs if k is not None}
    known_ids.update(kwargs)
    app_match = True if int(data.get('app_id', 0)) == int(FB_CLIENT_ID) else False
    data['app_connect'] = 'Not Found' if not app_match else data.get('is_valid', 'UNKNOWN')
    if 'user_id' in data:
        data_user_id = int(data.get('user_id', 0))
        data['user_connect'] = known_ids.get(data_user_id, data_user_id)
    scope_missing = set(FB_SCOPE)
    for ea in data.get('scopes', []):
        scope_missing.discard(ea)
    data['scope_missing'] = scope_missing
    if 'granular_scopes' in data:
        scope_detail = data['granular_scopes']
        for perm in scope_detail:
            if 'target_ids' in perm:
                perm['target_ids'] = [known_ids.get(int(ea), ea) for ea in perm['target_ids']]
        data['scope_detail'] = scope_detail
    return data


def inspect_access_token(input_token, app_access_token=None):
    """Confirm the access token is valid and belongs to this user. """
    app_access_token = app_access_token or generate_app_access_token()
    params = {'input_token': input_token, 'access_token': app_access_token}
    res = requests.get(FB_INSPECT_TOKEN_URL, params=params).json()
    if 'error' in res:
        app.logger.info('---------------- Error in inspect_access_token response ----------------')
        err = res.get('error', 'Empty Error')
        app.logger.error(f"Error: {err} ")
        return res  # err
    data = res.get('data', {})
    return data


def user_permissions(id_or_user, facebook=None, token=None, app_access_token=None):
    """Used by staff to check on what permissions a given user has granted to the platform application. """
    # TODO UNLIKELY: Is pagination a concern?
    user = find_valid_user(id_or_user)
    if not isinstance(user, User):
        app.logger.error("Expected a valid User instance, or id of one, for user_permissions check. ")
        return {}
    data = {'info': 'Permissions Report', 'id': user.id, 'name': user.name}
    keys = ('facebook_id', 'instagram_id', 'page_id', 'page_token', )
    needed = ', '.join(key for key in keys if not getattr(user, key, None))
    if user.story_subscribed is True:
        subscribed = True
    elif len(needed):
        subscribed = f"False, need {needed} "
    else:
        subscribed = "Have the account and page info, but NOT subscribed. "
    data['subscribed'] = subscribed

    token = token or user.token  # TODO: Determine if it should be user.full_token
    perm_info = {permission: False for permission in FB_SCOPE}  # Each will be overwritten if later found as True
    if facebook or token:
        url = f"https://graph.facebook.com/{user.facebook_id}/permissions"
        params = {}
        if not facebook:
            params['access_token'] = token
        res = facebook.get(url, params=params).json() if facebook else requests.get(url, params=params).json()
        if 'error' in res:
            app.logger.info('---------------- Error in user_permissions response ----------------')
            app.logger.error(f"Error: {res.get('error', 'Empty Error')} ")
        res_data = res.get('data', [{}])
        perm_info.update({ea.get('permission', ''): ea.get('status', '') for ea in res_data})
    data['facebook user permissions'] = ['{}: {}'.format(k, v) for k, v in perm_info.items()]

    if token:
        inspect = inspect_access_token(token, app_access_token)
        if 'error' not in inspect:
            inspect = pretty_token_data(inspect, fb_id=user.facebook_id, ig_id=user.instagram_id, page_id=user.page_id)
    else:
        skipped_text = "Not Known. Did not check due to lack of user token. "
        inspect = {'scope_missing': skipped_text, 'app_connect': skipped_text}
    missing_info = "Not Known. May need updated permissions. "
    missing_info += f"Confirm {user.name} has approved the Facebook application: {FB_CLIENT_APP_NAME} "
    data[f'Permission for {FB_CLIENT_APP_NAME}'] = inspect.get('app_connect', missing_info)
    data['Matching ID'] = inspect.get('user_connect', None)
    scope_missing = inspect.get('scope_missing', missing_info)  # default used only if received an error.
    scope_missing = scope_missing if len(scope_missing) else 'ALL GOOD'
    data['Permissions Needed'] = scope_missing
    data['Permission Details'] = inspect.get('scope_detail', 'Not Available')
    return data


def capture_media(post_or_posts, get_story_only):
    """DEPRECATED.
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
    """Get the insight metrics for the User. Has default values, but can be called with custom durations.
    It will check existing data to see how recently we have insight metrics for this user.
    It will request results for the full duration, or since recent data, or a minimum of 30 days.
    Returns a tuple of models and follow_report.
    """
    # TODO Priority 2: Is pagination a concern?
    ig_period = 'day'
    results, token = [], ''
    user = User.query.get(user_id)
    if not facebook or not ig_id:  # TODO: Use updated user.get_auth_session
        ig_id = ig_id or user.instagram_id
        token = user.token
    now = make_missing_timestamp(0)
    influence_date = user.recent_insight('influence')
    profile_date = user.recent_insight('profile')
    if influence_date:
        influence_last = max(30, int(min(influence_last, (now - influence_date).days)))
        app.logger.debug("Updated Influence Last. ")
    if profile_date:
        profile_last = max(30, int(min(profile_last, (now - profile_date).days)))
        app.logger.debug('Updated Profile Last')
    app.logger.info("------------ Get Insight: Influence, Profile ------------")
    app.logger.debug(influence_last)
    app.logger.debug(profile_last)

    for metric, last in zip(METRICS[Insight].values(), (influence_last, profile_last)):
        for i in range(first, last + first + 1 - 30, 30):
            until = now - timedelta(days=i)
            since = until - timedelta(days=30)
            url = f"https://graph.facebook.com/{ig_id}/insights"
            url += f"?metric={metric}&period={ig_period}&since={since}&until={until}"
            response = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
            insights = response.get('data', None)
            if not insights:
                app.logger.error('Error: ', response.get('error'))
                return None
            for ea in insights:
                for val in ea.get('values'):
                    val['name'], val['user_id'] = ea.get('name'), user_id
                    results.append(val)
    models = db_create_or_update_many(results, user_id=user_id, Model=Insight)
    follow_report = get_online_followers(user_id, ig_id=ig_id, facebook=facebook)
    logstring = "Added Online Followers data. " if follow_report else "No follow report. "
    app.logger.debug(logstring)
    return (models, follow_report)


def get_online_followers(user_id, ig_id=None, facebook=None):
    """Just want to get Facebook API response for online_followers for the maximum of the previous 30 days. """
    # app.logger.info('================ Get Online Followers data ================')
    # TODO Priority 2: Is pagination a concern?
    ig_period, token = 'lifetime', ''
    metric = METRICS[OnlineFollowers]
    if not facebook or not ig_id:  # TODO: Use updated user.get_auth_session
        user = User.query.get(user_id)
        ig_id = ig_id or user.instagram_id
        token = user.token
    start_days_ago = 1
    until = make_missing_timestamp(start_days_ago)
    since = make_missing_timestamp(start_days_ago + 30)
    url = f"https://graph.facebook.com/{ig_id}/insights"
    url += f"?metric={metric}&period={ig_period}&since={since}&until={until}"
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
    """Get the audience data for the (influencer or brand) user with given user_id """
    # app.logger.info('================ Get Audience Data ================')
    # TODO Priority 2: Is pagination a concern?
    metric = METRICS[Audience]
    ig_period = 'lifetime'
    results, token = [], ''
    if not facebook or not ig_id:  # TODO: Use updated user.get_auth_session
        user = User.query.get(user_id)
        ig_id = ig_id or user.instagram_id
        token = user.token
    url = f"https://graph.facebook.com/{ig_id}/insights"
    url += f"?metric={metric}&period={ig_period}"
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


def get_basic_post(media_id, metrics=None, id_or_user=None, facebook=None):
    """Returns API results of IG media posts content. Typically called by _get_posts_data_of_user.
    The user_id parameter can be a user instance or user_id.
    If there are issues in the data collection, sentinel values are saved in the 'caption' field.
    """
    # TODO: Is pagination a concern?
    auth = 'FACEBOOK' if facebook else 'NONE'
    user_id = None
    if not facebook:
        user = find_valid_user(id_or_user)
        if user:
            facebook = user.get_auth_session()
            user_id = user.id
    elif isinstance(id_or_user, (int, str)):
        user_id = int(id_or_user)
    elif isinstance(id_or_user, User):
        user_id = id_or_user.id
    else:
        app.logger.error("Expected a user id along with the facebook OAuth2Session passed. ")
    if not user_id or not isinstance(facebook, OAuth2Session):
        app.logger.error("The get_basic_post must be called with a User id or User that can create an auth seession. ")
    timestamp = str(make_missing_timestamp(0))
    empty_res = {'media_id': media_id, 'user_id': user_id, 'timestamp': timestamp, 'caption': 'NO_CREDENTIALS'}
    if not metrics:
        metrics = METRICS[Post]['basic']
    url = f"https://graph.facebook.com/{media_id}?fields={metrics}"
    try:
        res = facebook.get(url).json()
    except Exception as e:
        app.logger.info('------------- Error in get_basic_post FB API response -------------')
        app.logger.error(f"API fail for Post with media_id {media_id} | Auth: {auth} ")
        app.logger.exception(e)
        empty_res['caption'] = 'AUTH_' + auth
        return empty_res
    if 'error' in res:
        app.logger.info('------------- Error in get_basic_post FB API response -------------')
        app.logger.error(f"User: {id_or_user} | Media: {media_id} | Error: {res.get('error', 'Empty Error')} ")
        empty_res['caption'] = 'API_ERROR'
        return empty_res
    res_media_id = res.pop('id', '')
    if res_media_id != media_id:
        app.logger.error(f"Mismatch media_id: Request {media_id} | Response {res_media_id} ")
    res['media_id'] = media_id
    res['user_id'] = user_id
    return res


def get_metrics_post(media, facebook, metrics=None):
    """Takes in a dict already containing the data from get_basic_post and adds metrics data. """
    media_type = media['media_type']
    media_id = media['media_id']
    if not metrics:
        post_metrics = METRICS[Post]
        metrics = post_metrics.get(media_type, post_metrics['insight'])
        if metrics == post_metrics['insight']:
            app.logger.error(f" Match not found for {media_type} media_type parameter. ")
    url = f"https://graph.facebook.com/{media_id}/insights?metric={metrics}"
    res_insight = facebook.get(url).json()
    insights = res_insight.get('data')
    if insights:
        temp = {ea.get('name'): ea.get('values', [{'value': 0}])[0].get('value', 0) for ea in insights}
        if media_type == 'CAROUSEL_ALBUM':
            temp = {metric_clean(key): val for key, val in temp.items()}
        media.update(temp)
    else:
        app.logger.info(f"media {media_id} had NO INSIGHTS for type {media_type} --- {res_insight}. ")
    return media


def get_post_data(media_id, is_story=False, id_or_user=None, facebook=None):
    """Returns a dict with both basic and metrics data for a single media post (regular or story). """
    user = find_valid_user(id_or_user)
    if not user:
        return []
    facebook = facebook or user.get_auth_session()
    res = get_basic_post(media_id, id_or_user=user.id, facebook=facebook)
    res['media_type'] = 'STORY' if is_story else res.get('media_type', '')
    media = get_metrics_post(res, facebook=facebook)
    return media


def _get_posts_data_of_user(id_or_user, stories=True, ig_id=None, facebook=None):
    """Called by get_posts. Returns list, for a user, of STORY and regular media Posts with basic content & metrics. """
    # TODO: Is pagination a concern?
    user = find_valid_user(id_or_user)
    if not user:
        return []
    ig_id = ig_id or user.instagram_id
    facebook = facebook or user.get_auth_session()
    if not facebook:
        return []
    # if not facebook or not ig_id:
    #     ig_id = ig_id or user.instagram_id
    #     token = user.token
    # app.logger.info(f"==================== Get Posts on User {user_id} ====================")
    if stories:
        stories = user.get_media(story=True, facebook=facebook)
        # url = f"https://graph.facebook.com/{ig_id}/stories"
        # story_res = facebook.get(url).json()  # if facebook else requests.get(f"{url}?access_token={token}").json()
        # stories = story_res.get('data')
        # if not isinstance(stories, list) or 'error' in story_res:
        #     app.logger.error('Stories Error: ', story_res.get('error', 'NA'))
        stories = [get_post_data(ea.get('id'), is_story=True, id_or_user=user, facebook=facebook) for ea in stories]
    if not isinstance(stories, list):
        stories = []
    # story_ids = set(ea.get('id') for ea in stories)
    media = user.get_media(facebook=facebook)
    media = [get_post_data(ea.get('id'), id_or_user=user, facebook=facebook) for ea in media]
    results = stories + media
    # url = f"https://graph.facebook.com/{ig_id}/media"
    # response = facebook.get(url).json()  # if facebook else requests.get(f"{url}?access_token={token}").json()
    # media = response.get('data')
    # if not isinstance(media, list):
    #     app.logger.error('Error: ', response.get('error', 'NA'))
    #     media = []
    # media.extend(stories)
    # app.logger.info(f"------ Have a total of {len(media)} Media Posts, including {len(stories)} Stories ------")
    # post_metrics = METRICS[Post]
    # results = []
    # for post in media:
    #     media_id = post.get('id')
    #     res = get_basic_post(media_id, metrics=post_metrics['basic'], id_or_user=user, facebook=facebook, token=token)
    #     media_type = 'STORY' if media_id in story_ids else res.get('media_type', '')
    #     res['media_type'] = media_type
    #     metrics = post_metrics.get(media_type, post_metrics['insight'])
    #     if metrics == post_metrics['insight']:
    #         app.logger.error(f" Match not found for {media_type} media_type parameter. ")
    #     url = f"https://graph.facebook.com/{media_id}/insights?metric={metrics}"
    #     res_insight = facebook.get(url).json()  # if facebook else requests.get(f"{url}&access_token={token}").json()
    #     insights = res_insight.get('data')
    #     if insights:
    #         temp = {ea.get('name'): ea.get('values', [{'value': 0}])[0].get('value', 0) for ea in insights}
    #         if media_type == 'CAROUSEL_ALBUM':
    #             temp = {metric_clean(key): val for key, val in temp.items()}
    #         res.update(temp)
    #     else:
    #         app.logger.info(f"media {media_id} had NO INSIGHTS for type {media_type} --- {res_insight}. ")
    #     results.append(res)
    return results


def get_media_posts(id_or_users, stories=True, facebook=None, only_new=True):
    """Returns a list of saved Post objects created for the single or list of Users or User id(s).
    If stories parameter is 'only', then it will only get STORY media posts for these user(s).
    Otherwise stories parameter indicates if STORY media posts should or should not be included.
    This function is likely called by 'all_posts' for daily download or 'new_post' for a specific user.
    The Graph API is called to get all basic and metrics data, and creates or updates Posts in the database.
    Returns an array of the saved (created or updated) Post instances.
    """
    if not isinstance(id_or_users, (list, tuple)):
        id_or_users = [id_or_users]
    # results = []
    # for ea in id_or_users:
    #     results.extend(_get_posts_data_of_user(ea, stories=stories, ig_id=ig_id, facebook=facebook))
    users = (find_valid_user(ea) for ea in id_or_users)
    results = []
    for fb, user in ((facebook or u.get_auth_session(), u) for u in users if u):
        media = []  # currently want to include basic media after stories if getting both.
        if stories != 'only':
            media = user.get_media(use_last=only_new, facebook=fb)
            # if check_db:
            #     app.logger.debug("========== Check DB ==========")
            #     existing = Post.query.filter(Post.media_id in [int(ea) for ea in media]).options(load_only('media_id'))
            #     app.logger.debug(existing.all())
            #     existing = set(ea.media_id for ea in existing.all())
            #     app.logger.debug(existing)
            #     not_found = [ea for ea in media if int(ea) not in existing]
            media = [get_post_data(ea, id_or_user=user, facebook=fb) for ea in media]
        if stories:
            stories = user.get_media(story=True, facebook=fb)
            # stories = [get_post_data(ea, is_story=True, id_or_user=user, facebook=fb) for ea in stories]
            results.extend(get_post_data(ea, is_story=True, id_or_user=user, facebook=fb) for ea in stories)
        results.extend(media)
    if not results:
        return results
    saved = db_create_or_update_many(results, Post)
    # If any STORY posts were found, the SQLAlchemy Event Listener will add it to the Task queue for the Capture API.
    return saved


def get_fb_page_for_users_ig_account(user, ignore_current=False, facebook=None, token=None):
    """For a user with a known Instagram account, we can determine the related Facebook page. """
    # TODO: Is pagination a concern?
    if not isinstance(user, User):
        raise Exception("get_fb_page_for_users_ig_account requires a User model instance as the first parameter. ")
    page = dict(zip(['id', 'token'], [getattr(user, 'page_id', None), getattr(user, 'page_token', None)]))
    if ignore_current or not page.get('id') or not page.get('token'):
        ig_id = int(getattr(user, 'instagram_id', 0))
        fb_id = getattr(user, 'facebook_id', 0)
        if not ig_id or not fb_id:
            message = "We can only get a users page if we already know their accounts on Facebook and Instagram. "
            app.logger.error(message)
            return None
        if not facebook and not token:
            token = getattr(user, 'token', None)
            if not token:
                message = f"We do not have the permission token for this user: {user} "
                app.logger.error(message)
                return None
        url = f"https://graph.facebook.com/{fb_id}"
        # app.logger.info(f"========== get_fb_page_for_users_ig_account {user} ==========")
        params = {'fields': 'accounts'}
        if not facebook:
            params['access_token'] = token
        res = facebook.post(url, params=params).json() if facebook else requests.post(url, params=params).json()
        # pprint(res)
        accounts = res.pop('accounts', None)
        ig_list = find_instagram_id(accounts, facebook=facebook, token=token)
        matching_ig = [ig_info for ig_info in ig_list if int(ig_info.get('id', 0)) == ig_id]
        ig_info = matching_ig[0] if len(matching_ig) == 1 else {}
        page = {'id': ig_info.get('page_id'), 'token': ig_info.get('page_token'), 'new_page': True}
    success = True if page['id'] and page['token'] else False
    return page if success else None


def install_app_on_user_for_story_updates(id_or_user, page=None, facebook=None, token=None):
    """Accurate Story Post metrics can be pushed to the Platform only if the App is installed on the related Page. """
    # TODO: Is pagination a concern?
    user = find_valid_user(id_or_user)
    # app.logger.info(f"========== INSTALL APP for: {user} ==========")
    if not isinstance(page, dict) or not page.get('id') or not page.get('token'):
        page = get_fb_page_for_users_ig_account(user, facebook=facebook, token=token)
        if not page:
            app.logger.error(f"Unable to find the page for user: {user} ")
            return False
    url = f"https://graph.facebook.com/{page['id']}/subscribed_apps"  # TODO: Works, but FB docs indicate v# required.
    # url = f"https://graph.facebook.com/v9.0/{page['id']}/subscribed_apps",  # TODO: v3.1 out of date, is v# needed?
    field = 'name'  # OPTIONS: 'category', 'website' # NOT VALID: 'has_added_app', 'is_owned'
    # TODO: Check if permission needed: pages_manage_metadata or pages_read_user_content
    params = {} if facebook else {'access_token': page['token']}  # TODO: Determine if always need page access token.
    params['subscribed_fields'] = field
    res = facebook.post(url, params=params).json() if facebook else requests.post(url, params=params).json()
    app.logger.info(f"======== Install App for {user.name} - Success: {res.get('success', False)} ========")
    errors = []
    if 'error' in res:
        common_error_strings = {
            'two factor auth': 'requires Two Factor Authentication, the user also needs to enable Two Factor Auth',
            'permissions': 'permissions is needed',
            'admin level': 'does not have sufficient administrative',
            'not authorized': 'has not authorized application',
            'pages_read_engagement': 'pages_read_engagement',
            'pages_read_user_content': 'pages_read_user_content',
            'pages_show_list': 'pages_show_list',
            'pages_manage_metadata': 'pages_manage_metadata',
        }
        message = res['error'].get('message')
        for key, value in common_error_strings.items():
            if value in message:
                errors.append(key)
    if errors:
        app.logger.error(f"Found errors: {errors} ")
    else:
        pprint(res)
    return res.get('success', False)


def remove_app_on_user_for_story_updates(id_or_user, page=None, facebook=None, token=None):
    """This User is no longer having their Story Posts tracked, so uninstall the App on their related Page. """
    user = find_valid_user(id_or_user)
    app.logger.info(f"========== remove_app_on_user_for_story_updates: {user} ==========")
    return True
    # if not isinstance(page, dict) or not page.get('id') or not page.get('token'):
    #     page = get_fb_page_for_users_ig_account(user, facebook=facebook, token=token)
    #     if not page:
    #         app.logger.error(f"Unable to find the page for user: {user} ")
    #         return False
    # url = f"https://graph.facebook.com/v3.1/{page['id']}/subscribed_apps"  # TODO: v3.1 it out of date?
    # TODO: Check if permission needed: pages_manage_metadata or pages_read_user_content
    # params = {} if facebook else {'access_token': page['token']}
    # params['subscribed_fields'] = ''  # Remove all despite docs saying parameter cannot configure Instagram Webhooks
    # res = facebook.post(url, params=params).json() if facebook else requests.post(url, params=params).json()
    # # TODO: See if facebook with params above works.
    # app.logger.info('----------------------------------------------------------------')
    # pprint(res)
    # return res.get('success', False)


def get_ig_info(ig_id, facebook=None, token=None):
    """We already have their InstaGram Business Account id, but we need their IG username """
    # Possible fields. Fields with asterisk (*) are public and can be returned by and edge using field expansion:
    # biography*, id*, ig_id, followers_count*, follows_count, media_count*, name,
    # profile_picture_url, username*, website*
    # TODO: Is pagination a concern?
    fields = ','.join(['username', *Audience.IG_DATA])  # 'media_count', 'followers_count'
    app.logger.info('============ Get IG Info ===================')
    if not token and not facebook:
        logstring = "You must pass a 'token' or 'facebook' reference. "
        app.logger.error(logstring)
        raise ValueError(logstring)
    url = f"https://graph.facebook.com/v4.0/{ig_id}?fields={fields}"
    res = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
    end_time = make_missing_timestamp(0).isoformat(timespec='seconds') + '+0000'
    for name in Audience.IG_DATA:  # {'media_count', 'followers_count'}
        res[name] = {'end_time': end_time, 'value': res.get(name)}
    res['name'] = res.pop('username', res.get('name', ''))
    return res


def find_pages_for_fb_id(fb_id, facebook=None, token=None):
    """From a known facebook id, we can get a list of all pages the user has a role on via the accounts route.
    Using technique from Graph API docs: https://developers.facebook.com/docs/graph-api/reference/v7.0/user/accounts
    Returns the response received from the Graph API.
    """
    # TODO Priority 2: CHECK FOR PAGINATION
    url = f"https://graph.facebook.com/v7.0/{fb_id}/accounts"
    # app.logger.info("========================== The find_pages_for_fb_id was called ==========================")
    if not facebook and not token:
        message = "This function requires at least one value for either 'facebook' or 'token' keyword arguments. "
        app.logger.error(message)
        raise Exception(message)
    params = {} if facebook else {'access_token': token}
    res = facebook.get(url).json() if facebook else requests.get(url, params=params).json()
    if 'error' in res:
        app.logger.error('Got error in find_pages_for_fb_id function')
        app.logger.error(res['error'])
        # TODO: Handle error.
    # TODO: Confirm 'res' is formatted to match what is expected for 'accounts'
    return res


def find_instagram_id(accounts, facebook=None, token=None, app_token=None):
    """For an influencer or brand, we can discover all of their instagram business accounts they have.
       This depends on them having their expected associated facebook page (for each).
    """
    # TODO: Handle pagination results on 'accounts' of FB Pages? Unlikely issue for instagram_business_account request.
    if not facebook and not token:
        message = "This function requires at least one value for either 'facebook' or 'token' keyword arguments. "
        app.logger.error(message)
        return []  # raise Exception(message)
    if not accounts or 'data' not in accounts:
        message = f"No pages found from accounts data: {accounts}. "
        app.logger.error(message)
        return []
    if 'paging' in accounts:
        app.logger.info(f"Have paging in accounts: {accounts['paging']} ")
        # TODO: Handle paging in results.
    ig_list = []
    pages = [{'id': page.get('id'), 'token': page.get('access_token')} for page in accounts.get('data')]
    app.logger.info(f"============ Pages count: {len(pages)} ============")
    for page in pages:
        # url = f"https://graph.facebook.com/v4.0/{page['id']}?fields=instagram_business_account"
        url = f"https://graph.facebook.com/{page['id']}?fields=instagram_business_account"
        # Docs: https://developers.facebook.com/docs/instagram-api/reference/page
        req_token, err, res = page['token'], 10, None
        while err > 1:
            res = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={req_token}").json()
            if 'error' in res and res['error'].get('code', 0) in (100, 190) and not facebook:
                if err == 10:
                    err = 100
                    req_token = token
                    app.logger.info("Will use app token for user. ")
                elif err == 100:
                    err = 200
                    app.logger.info("Will use a generated app token. ")
                    req_token = app_token or generate_app_access_token()
                else:
                    app.logger.info("Tried page token, user token, and generated token. All have failed. ")
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
        else:
            app.logger.info(f"No appropriate account on {page['id']} Page. ")
    return ig_list


def onboard_login(mod):
    """Process the initiation of creating a new influencer or brand user with facebook authorization. """
    callback = URL + '/callback/' + mod
    facebook = OAuth2Session(FB_CLIENT_ID, redirect_uri=callback, scope=FB_SCOPE)
    facebook = facebook_compliance_fix(facebook)  # we need to apply a fix for Facebook here
    authorization_url, state = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)
    session['oauth_state'] = state.strip()
    app.logger.info("================ Login Function Paramters ================")
    app.logger.info(f"mod: {mod} ")
    app.logger.info(f"callback: {callback} ")
    app.logger.info(f"authorization_url: {authorization_url} ")
    app.logger.info(f"Session State: {session['oauth_state']} ")
    app.logger.info("=========================================================")
    return authorization_url


def onboard_new(data, facebook=None, token=None):
    """Typically used for adding a user that does not have any accounts under their facebook id.
    May also be used for a currently logged in user to create another account with a different Instagram account.
    The user should be logged in before returning results, but only if valid Instagram account(s) are found.
    Returns a tuple of a string for the state results and a list of professional instagram account(s) 'ig_info'.
    """
    if not facebook and not token:
        message = "This function requires at least one value for either 'facebook' or 'token' keyword arguments. "
        app.logger.error(message)
        return ('not_found', [])  # raise Exception(message)
    fb_id = data.get('facebook_id', '')
    accounts = data.pop('accounts', None) or find_pages_for_fb_id(fb_id, facebook=facebook, token=token)
    ig_list = find_instagram_id(accounts, facebook=facebook, token=token)
    ig_id, user = None, None
    if len(ig_list) == 0:
        app.logger.info("No valid instagram accounts were found. ")
        return ('not_found', ig_list)
    if current_user.is_authenticated and getattr(current_user, 'facebook_id', None) == fb_id:
        # This is the case when a current user is creating another user account with a different Instagram account.
        if token:
            data['token'] = token
        if fb_id:
            data['name'] = fb_id
        user = User.query.filter(User.name == fb_id, User.facebook_id == fb_id, User.id != current_user.id).first()
        logout_user()
        # TODO: Complete modifications needed for creating another user account.
        app.logger.debug(f'------ Found {len(ig_list)} potential IG accounts ------')
    elif len(ig_list) == 1:
        ig_info = ig_list[0]
        data['name'] = ig_info.get('name', None)
        ig_id = int(ig_info.get('id', 0))
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
        data['name'] = data.get('facebook_id', data.get('id', None)) if 'name' not in data else data['name']
        app.logger.debug(f'------ Found {len(ig_list)} potential IG accounts ------')
    # TODO: Create and use a User method that will create or use existing User, and returns a User object.
    # Refactor next three lines to utilize this method so we don't need the extra query based on id.
    if not user:
        account = db_create(data)
        user = User.query.get(account.get('id'))
    else:
        app.logger.info(f"Found existing user account {user}. ")
        # TODO: Update user with data values.
    login_user(user, force=True, remember=True)
    for ig_info in ig_list:
        ig_info.update({'account_id': user.id})
    if ig_id:
        # previous versions called get_insight and get_audience. These will need to be called manually later.
        return ('complete', ig_list)
    else:  # This Facebook user needs to select one of many of their IG business accounts
        return ('decide', ig_list)


def user_update_on_login(user, data, ig_list):
    """During login of existing user, update their user model with recent information. """
    data_token = data.get('token', None)
    if data_token and data_token != user.full_token:  # TODO: Determine if it should be user.full_token or user.token
        user.token = data_token  # TODO: confirm this is saved by some automatic db.session.commit()
        user.token_expires = data.get('token_expires', None)
    if len(ig_list) == 1:  # this user is missing page_id or page_token, and there is only 1 option.
        ig_info = ig_list[0]
        user.page_id = ig_info.get('page_id')
        user.page_token = ig_info.get('page_token')
        if not user.instagram_id:
            user.name = ig_info.get('name', user.name)
            user.instagram_id = int(ig_info.get('id', 0))
            models = []
            for name in Audience.IG_DATA:  # {'media_count', 'followers_count'}
                value = ig_info.get(name, None)
                if value:
                    models.append(Audience(name=name, values=[value]))
            user.audiences.extend(models)
        app.logger.debug('------ Only 1 InstaGram business account for onboard_existing ------')
    elif len(ig_list) > 1:  # this user is missing page_id or page_token, unsure which to use.
        app.logger.debug(f'------ Found {len(ig_list)} IG Pages for onboard_existing ------')
    return user


def onboard_existing(users, data, facebook=None):
    """Login an existing user. If multiple users under the same facebook id, return a list of users to switch to. """
    login_user(users[0], force=True, remember=True)
    data = translate_api_user_token(data)
    missing_page_info = any(not u.page_id or not u.page_token for u in users)
    if missing_page_info:
        accounts = data.pop('accounts', None)
        ig_list = find_instagram_id(accounts, facebook=facebook)
        ig_id_targets = set(u.instagram_id for u in users if u.instagram_id)
        if len(ig_id_targets):
            ig_list = [ig_info for ig_info in ig_list if int(ig_info.get('id', 0)) in ig_id_targets]
    else:
        ig_list = []
    if len(users) == 1:
        user = users[0]
        user = user_update_on_login(user, data, ig_list)
        return ('complete', [{'account_id': user.id}])
    user_list = []
    for user in users:
        if all(user.instagram_id, user.page_id, user.page_token):
            cur_ig_list = []
        elif user.instagram_id and len(ig_list):
            cur_ig_list = [ig_info for ig_info in ig_list if int(ig_info.get('id', 0)) == user.instagram_id]
        else:
            cur_ig_list = ig_list
        user = user_update_on_login(user, data, cur_ig_list)
        ig_info = {'account_id': user.id, 'name': user.name, 'followers_count': 'unknown', 'media_count': 'unknown'}
        # ig_info['name'] = user.name
        # ig_info['id'] = user.instagram_id
        # ig_info['followers_count'] = ''  # Will be skipped in manage.process_form
        # ig_info['media_count'] = ''  # Will be skipped in manage.process_form
        # ig_info['page_id'] = user.page_id
        # ig_info['page_token'] = user.page_token
        user_list.append(ig_info)
    return ('existing', user_list)


def onboarding(mod, request):
    """Verify the authorization request. Then either login or create the appropriate influencer or brand user.
    Input mod: The mod value for the user role. The only valid values for the API callback are 'influencer' or 'brand'.
    Input request: The request object received by this application.
    view: a string that can be one of: 'complete', 'decide', 'existing', 'not_found', 'error'.
    ig_info: is a dict of the error or pertinent information about a connected professional instagram account(s).
    Non-error 'ig_info' have the keys: account_id, name, facebook_id, followers_count, media_count, page_id, page_token.
    Behavior: User is logged in to an existing or created (if there is a valid Instagram account) User account.
    Returns a tuple of a 'view' and a list of 'ig_info' as defined above.
    """
    callback = URL + '/callback/' + mod
    request_url = request.url.strip().rstrip('#_=_')
    params = request.args
    state = params.get('state', None)
    url_diff = str(request.url).lstrip(request_url)
    app.logger.info("================ Onboarding Function Paramters ================")
    app.logger.info(f"mod: {mod} ")
    app.logger.info(f"callback: {callback} ")
    app.logger.info(f"Url Cleaned unchanged: {str(request.url) == request_url} ")
    app.logger.info(f"Url diff: {url_diff} ")
    app.logger.info(f"Session-State: {session.get('oauth_state')} ")
    app.logger.info(f"Params--State: {state} ")
    app.logger.info(state == session.get('oauth_state', ''))
    app.logger.info("=========================================================")
    facebook = OAuth2Session(FB_CLIENT_ID, scope=FB_SCOPE, redirect_uri=callback)  # , state=session.get('oauth_state')
    facebook = facebook_compliance_fix(facebook)  # we need to apply a fix for Facebook here
    # TODO: ? Modify input parameters to only pass the request.url value since that is all we use?
    token = facebook.fetch_token(FB_TOKEN_URL, client_secret=FB_CLIENT_SECRET, authorization_response=request_url)
    # The previous line likely does the exchange of 'code' for the Access Token (probably long-lasting. )
    app.logger.info(token)
    if 'error' in token:
        app.logger.info(token['error'])
        return ('error', token['error'])
    url = "https://graph.facebook.com/me?fields=id,accounts"  # For FB Pages.
    facebook_user_data = facebook.get(url).json()  # Docs don't mention pagination, imply not a concern yet.
    # TODO UNLIKELY?: Is pagination a concern?
    if 'error' in facebook_user_data:
        app.logger.info(facebook_user_data['error'])
        return ('error', facebook_user_data['error'])
    data = facebook_user_data.copy()  # .to_dict(flat=True)
    data['role'] = mod
    data['token'] = token
    fb_id = data.get('id', None)  # TODO: Change to .pop once confirmed elsewhere always looks for 'facebook_id'.
    data['facebook_id'] = fb_id
    # app.logger.info('================ Prepared Data and Users ================')
    # app.logger.info(data)
    users = User.query.filter(User.facebook_id == fb_id).all() if fb_id else None
    # app.logger.info(users)
    # app.logger.info('=========================================================')
    if users:
        return onboard_existing(users, data, facebook=facebook)
    else:
        return onboard_new(data, facebook=facebook)
