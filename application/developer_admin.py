from flask import json, render_template, flash, request, current_app as app
from flask_login import current_user
from .helper_functions import staff_required  # , mod_lookup
from .model_db import Campaign, User, db  # , create_many
from .api import get_fb_page_for_users_ig_account, user_permissions, generate_app_access_token  # , get_ig_info
from .api import FB_CLIENT_APP_NAME
from .events import handle_campaign_stories, session_user_subscribe
from pprint import pprint


def admin_view(data=None, files=None):
    """Platform Admin view to display links and actions unique to admin """
    dev_email = ['hepcatchris@gmail.com', 'christopherlchapman42@gmail.com']
    dev = current_user.email in dev_email
    return render_template('admin.html', dev=dev, data=data, files=files)


def admin_report_view(mod, info=None, overview=None, files=None):
    """Platform Admin view for larger report display. """
    # files = None if app.config.get('LOCAL_ENV') else all_files()
    return render_template('admin_report.html', mod=mod, info=info, overview=overview, files=files)


def query_by_kwargs(query, Model=User, active_campaigns=None, **kwargs):
    """Returns a query based on the given query and kwargs. """
    q = query
    for key, val in kwargs.items():
        if isinstance(val, (list, tuple)):
            q = q.filter(getattr(Model, key).in_(val))
        elif isinstance(val, bool):
            q = q.filter(getattr(Model, key).is_(val))
        elif isinstance(val, type(None)) or val in ('IS NOT TRUE', 'IS NOT FALSE'):
            if val is not None:
                val = True if val == 'IS NOT TRUE' else False
            q = q.filter(getattr(Model, key).isnot(val))
        elif isinstance(val, (str, int, float)):
            q = q.filter(getattr(Model, key) == val)
        else:
            app.logger.error(f"Unsure how to filter for type {type(val)} for key: value of {key}: {val} ")
    result = None
    if active_campaigns is not None:  # expected value True or False, left as None if not filtering by this.
        if Model == User:
            result = [u for u in q.all() if u.has_active_all is active_campaigns]
        elif Model == Campaign:
            q = q.filter(Campaign.completed is False)
    return result or q.all()


def get_pages_for_users(overwrite=False, remove=False, **kwargs):
    """Gets or updates the appropriate Facebook Pages, and triggers the appropriate setting of user.story_subscribed
    The webhooks story_insights subscription setup depends on the Facebook Page of the professional instagram account.
    If not already saved, will try to reconcile if the Facebook Page id, or needed permission token for the page.
    Despite any setting of user.story_subscribed, its final value depends on Events triggered by the database commit.
    Input overwrite: If this function should try to replace the user page_id and page_token values.
    Input remove: If the set of users should have their story_subscribed set to False (under appropriate conditions).
    Input kwargs: Determines which group of users are managed by this process.
    Returns a dict of paired user ids and str of user instance of users updated in the database commit.
    """
    updates = {}
    q = User.query.filter(User.instagram_id.isnot(None))
    users = query_by_kwargs(q, kwargs)
    active_campaigns = kwargs.get('active_campaigns', None)
    for user in users:
        page = get_fb_page_for_users_ig_account(user)
        if remove and user.story_subscribed:
            session_user_subscribe(user, remove=True)  # Okay because we already filtered to users without has_active
            page_token = page.get('token', None) or getattr(user, 'page_token', None)
            user.page_token = page_token  # Triggers checking for active Campaigns, and ensures a flush.
            db.session.add(user)
            updates[user.id] = str(user)
        if page and (overwrite or page.get('new_page')):
            user.page_id = page.get('id')
            user.page_token = page.get('token')
            db.session.add(user)
            updates[user.id] = str(user)
        elif page and active_campaigns and not user.story_subscribed:
            session_user_subscribe(user)
            old_notes = user.notes or ''
            user.notes = old_notes + ' add story_insights'  # Ensures a flush.
            db.session.add(user)
            updates[user.id] = str(user)
    db.session.commit()
    return updates


def permission_check_many(**kwargs):
    """Allows admin to check for problems with Graph API permissions on groups of users. """
    users = query_by_kwargs(User.query, **kwargs)
    app_access_token = generate_app_access_token()
    results = {user: user_permissions(user, app_access_token=app_access_token) for user in users}
    return results


def make_permission_overview(data):
    """For a given permission report data, return an overview dict. """
    overview = {}
    for user, info in data.items():
        user_keys = ['facebook_id', 'instagram_id', 'page_id', 'page_token']
        needed = ', '.join(key for key in user_keys if not getattr(user, key, None))
        if user.token:
            err_str = 'Not Known'
            keys = [(f'Permission for {FB_CLIENT_APP_NAME}', 'Platform'), ('Permissions Needed', 'Need Scope')]
            label_vals = []
            for key, label in keys:
                val = info.get(key, None)
                if isinstance(val, (list, tuple)):
                    val = ', '.join(val)
                elif val is None:
                    val = ''
                else:
                    val = str(val)
                if val.startswith(err_str):
                    val = err_str
                label_vals.append((label, val, ))
            info_summary = [f"{k}: {v}" for k, v in label_vals if v]
            if needed:
                info_summary.append(f"Missing: {needed}")
        else:
            info_summary = [f"Missing: {needed}"] if needed else []
            info_summary.append('user token')
        info_summary = ', '.join(info_summary)
        attr = 'list' if info_summary.endswith('ALL GOOD') else 'error'
        overview[user] = {'attr': attr, 'text': info_summary}
    return overview


@app.route('/report/<string:group>')
@staff_required()
def permission_report(group):
    """Collects and displays Permission Reports for platform users. """
    id_list = request.args.get('ids', '').split(',')
    opts = {
        'all': {},
        'active': {'active_campaigns': True, },
        'inactive': {'active_campaigns': False, },
        'unsubscribed': {'story_subscribed': False, },
        'listed': {'id': [] if id_list == [''] else [int(ea) for ea in id_list]},
    }
    data = permission_check_many(**opts[group])
    if not data:
        flash("Error in Permission Report - looking up permission granted by platform users. ")
        overview = None
    else:
        flash(f"Permission Report for {group} users, with {len(data)} results. ")
        overview = make_permission_overview(data)
    return admin_report_view('permissions', info=data, overview=overview)


@app.route('/subscribe/<string:group>')
@staff_required()
def subscribe_pages(group):
    """Used by admin to subscribe to all current platform user's facebook page, if they are not already subscribed. """

    app.logger.debug(f"=============== subscribe_pages: {group} ===============")
    if group == 'active':  # For every user in an active campaign, add them to db.session.info['subscribe_page'] set.
        active_campaigns = Campaign.query.filter(Campaign.completed is False)
        for ea in active_campaigns:
            handle_campaign_stories(ea, False, 'Fake Old Value', 'Manual_Call')
        # db.session.commit()
    param_lookup = {
        'all': {'page_id': None, 'overwrite': True, },
        'token': {'page_token': None, 'overwrite': True, },
        'active': {'active_campaigns': True, 'overwrite': False, },
        'remove': {'active_campaigns': False, 'remove': True, 'overwrite': False, },
        # 'remove_all': {'remove': True, 'overwrite': False, },
        'all_force': {'overwrite': True, },
        'inactive_force': {'story_subscribed': 'IS NOT TRUE', 'overwrite': True, },
        'active_force': {'story_subscribed': True, 'overwrite': True, },
    }
    column_args = param_lookup.get(group, {})
    all_response = get_pages_for_users(**column_args)
    if app.config.get('DEBUG'):
        app.logger.debug(f"--------------- Results subscribe {group} ---------------")
        pprint(all_response)
        app.logger.debug(f"--------------- End subscribe {group} ---------------")
    return admin_view(data=all_response)


@app.route('/<string:mod>/<int:id>/subscribe')
@staff_required()
def subscribe_page(mod, id):
    """NOT IMPLEMENTED. Used by admin manually subscribe to this user's facebook page. """
    pass


@app.route('/deletion')
def fb_delete():
    """NOT IMPLEMENTED.
        Handle a Facebook Data Deletion Request
        More details: https://developers.facebook.com/docs/apps/delete-data
    """
    response = {}
    response['user_id'] = 'test user_id'
    response['url'] = 'see status of deletion'
    response['confirmation_code'] = 'some unique code'
    # TODO: do stuff
    return json.dumps(response)
