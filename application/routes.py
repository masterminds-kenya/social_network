from flask import render_template, redirect, url_for, request, flash, session, current_app as app  # , abort
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import json
from .model_db import db_create, db_read, db_delete, db_all, from_sql  # , metric_clean
from .model_db import User, OnlineFollowers, Insight, Post, Campaign  # , db, Audience
from .developer_admin import admin_view
from .helper_functions import staff_required, admin_required, mod_lookup, prep_ig_decide, get_daily_ig_accounts
from .manage import update_campaign, process_form, report_update, check_hash, add_edit, media_posts_save, process_hook
from .api import (onboard_login, onboarding, user_permissions, get_insight, get_audience, get_online_followers,
                  get_media_lists, get_metrics_media, handle_collect_media)
from .create_queue_task import add_to_collect
from .sheets import create_sheet, update_sheet, perm_add, perm_list, all_files
from pprint import pprint

# Sentinels for errors recorded on the Post.caption field.
caption_errors = ['NO_CREDENTIALS', 'AUTH_FACEBOOK', 'AUTH_TOKEN', 'AUTH_NONE', 'API_ERROR', 'INSIGHTS_CREATED']


def test_local(*args, **kwargs):
    """Useful for constructing tests, but will only work when running locally. """
    app.logger.info("========== Home route run locally ==========")
    session['hello'] = 'Hello Session World'
    app.logger.info(session)
    local_data = {
        'page': 'Proof of Life',
        'text': 'Does this text get there?',
        'info_list': ['first_item', 'second_item', 'third_item'],
        'data': json.dumps({'first': 'val_1', 'second': 'val_2'})
    }
    return local_data


@app.route('/')
def home():
    """Default root route """
    local_data = None
    if app.config.get('LOCAL_ENV', False):
        local_data = test_local()
    return render_template('index.html', local_data=local_data)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Using Flask-Login to create a new user (manager or admin) account """
    app.logger.info('--------- Sign Up User ------------')
    ignore = ['influencer', 'brand']
    signup_roles = [role for role in User.ROLES if role not in ignore]
    if request.method == 'POST':
        mod = request.form.get('role')
        if mod not in signup_roles:
            raise ValueError("That is not a valid role selection. ")
        data = process_form(mod, request)
        password = data.get('password', None)
        # TODO: allow system for an admin to create a user w/o a password,
        # but require that user to create a password on first login
        admin_create = False
        if not password and not admin_create:
            flash("A password is required. ")
            return redirect(url_for('signup'))
        else:
            data['password'] = generate_password_hash(password)
        user = User.query.filter_by(name=data['name']).first()
        if user:
            flash("That name is already in use. ")
            return redirect(url_for('signup'))
        user = User.query.filter_by(email=data['email']).first()
        if user:
            flash("That email address is already in use. ")
            return redirect(url_for('signup'))
        user = db_create(data)
        flash("You have created a new user account! ")
        return redirect(url_for('view', mod=mod, id=user['id']))

    next_page = request.args.get('next')
    if next_page == url_for('list_all', mod='influencer'):
        mods = ['influencer']
    elif next_page == url_for('list_all', mod='brand'):
        mods = ['brand']
    else:
        mods = ['influencer', 'brand']
    return render_template('signup.html', signup_roles=signup_roles, mods=mods)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """This the the manual login process. """
    if request.method == 'POST':
        data = process_form('login', request)
        password = data.get('password', None)
        if not password:
            flash("Password required. If you don't have one, you can try Facebook login, otherwise contact an admin. ")
            return redirect(url_for('login'))
        user = User.query.filter_by(email=data['email']).first()
        # app.logger.debug(f"Found {user} user with role {getattr(user, 'role', 'NOT FOUND')}. ")
        if not user or not check_password_hash(user.password, data['password']):
            app.logger.debug("Problem with login credentials. ")
            if user:
                app.logger.debug(f"Password problem for {user} ")
            flash("Those login details did not work. ")
            return redirect(url_for('login'))
        attempt = login_user(user, remember=data.get('remember', False))  # , duration=timedelta(days=61)
        if not attempt:
            app.logger.debug(f"The login attempt response: {attempt} ")
        # app.logger.debug(f"Current User: {current_user}, is a good match: {current_user == user} ")
        # if current_user == user:
        #     app.logger.debug(f"Current details | role: {user.role} | id: {user.id} | is_active: {getattr(user, 'is_active', 'NOT FOUND')} ")
        return view(user.role, user.id)
        # return redirect(url_for('view', mod=user.role, id=user.id))
    return render_template('signup.html', signup_roles=None, mods=['influencer', 'brand'])


@app.route('/logout')
@login_required
def logout():
    """Logs out current user and redirects them to the home page. """
    logout_user()
    flash("You are now logged out. ")
    return redirect(url_for('home'))


@app.route('/error', methods=['GET', 'POST'])
def error():
    """Error route. """
    err = request.form.get('data') or request.args
    app.logger.error(err)
    if not app.config.get('DEBUG'):
        err = None
    return render_template('error.html', err=err)


@app.route('/admin')
@admin_required()
def admin():
    """Admin page view, which may have some data or files to display as summary of work progress. """
    data = request.args.get('data', None)
    files = request.args.get('files', None)
    return admin_view(data=data, files=files)


@app.route('/<string:mod>/<int:id>/permissions')
@staff_required()
def permission_check(mod, id):
    """Used by admin to see what permissions a given user has granted the platform """
    if mod_lookup(mod) != User:
        flash("Not a valid mod value for this function. ")
        return redirect(request.referrer)
    user = User.query.get(id)
    data = user_permissions(user)
    if not data:
        flash("Error in looking up permission granted by the user to the platform. ")
        return redirect(request.referrer)
    app.logger.info(f"========== PERMISSION CHECK: {user} ===========")
    pprint(data)
    return render_template('view.html', mod=mod, data=data)


@app.route('/data/post/problem')
@admin_required()
def problem_posts():
    """These media posts experienced problems that should be investigated. """
    null_date = '2020-12-16'
    problem_data = Post.query.filter(Post.caption.in_(caption_errors))
    recent_null = Post.query.filter(Post.caption.is_(None), Post.created > null_date)
    models = problem_data.union(recent_null)
    problem_posts = models.all()
    data = {'posts': problem_posts}
    mod = 'error media posts'
    template = 'view.html'
    flash(f"All media posts received with either NULL after {null_date} or assigned a caption error code. ")
    flash(f"Known caption error codes: {', '.join(caption_errors)}. ")
    return render_template(template, mod=mod, data=data, caption_errors=caption_errors)


@app.route('/admin/test')
@admin_required()
def test_method():
    """Temporary restricted to admin route and function for developer to test components. """
    from .create_queue_task import list_queues
    app.logger.info("========== Test Method for admin:  ==========")
    info = list_queues()
    # info = get_daily_ig_accounts()
    # pprint([f"{ea}: {len(ea.campaigns)} | {len(ea.brand_campaigns)} " for ea in info])
    # info = {'key1': 1, 'key2': 'two', 'key3': '3rd', 'meaningful': False}
    # pprint(info)
    app.logger.info('-------------------------------------------------------------')
    return redirect(url_for('admin', data=info))


@app.route('/any/test')
def open_test(**kwargs):
    """Temporary open public route and function for developer to test components without requiring a login. """
    # TODO: Confirm this open route is closed before pushing to production.
    if not app.config.get('LOCAL_ENV', False):
        app.logger.info("========== Test Method Open: Error  ==========")
        return redirect(url_for('error', **request.args))
    app.logger.info("========== Test Method Open  ==========")
    hello_val = session.get('hello', 'NOT FOUND')
    app.logger.info(hello_val)
    app.logger.info("----------------------------------------------------")
    app.logger.info(session)
    app.logger.info("----------------------------------------------------")
    params = request.args.to_dict(flat=False)
    params = {k: params[k][0] if len(params[k]) < 2 else params[k] for k in params}
    kwargs.update(params)
    page_title = kwargs.pop('page', None)
    text = kwargs.pop('text', '')
    info = kwargs.pop('info_list', [])
    data = kwargs.pop('data', {})
    if isinstance(data, str):
        data = json.loads(data)
    template = kwargs.pop('template', 'simple.html')
    return render_template(template, page=page_title, text=text, info_list=info, data=data, other=kwargs)


@app.route('/data/capture/<int:id>')
@admin_required()
def capture(id):
    """Manual call to capture the media files. Currently on an Admin function, to be updated later. """
    from .events import enqueue_capture

    post = Post.query.get(id)
    if not post:
        message = "Post not found. "
        app.logger.info(message)
        flash(message)
        return redirect(url_for('admin'))
    value = post.media_type
    ret_value = enqueue_capture(post, value, value, 'Admin Capture Route')
    message = f"Added {post} to capture queue. " if value == ret_value else f"Unable to add {post} to capture queue. "
    flash(message)
    return redirect(url_for('admin'))


# ########## The following are for worksheets ############


@app.route('/<string:mod>/<int:id>/export', methods=['GET', 'POST'])
@staff_required()
def export(mod, id):
    """Export data to google sheet, generally for influencer or brand Users. Linked in the view template. """
    app.logger.info(f"==== {mod} Create Sheet ====")
    Model = mod_lookup(mod)
    model = Model.query.get(id)
    sheet = create_sheet(model)
    return render_template('data.html', mod=mod, id=id, sheet=sheet)


@app.route('/data/update/<string:mod>/<int:id>/<string:sheet_id>')
@staff_required()
def update_data(mod, id, sheet_id):
    """Update the given worksheet (sheet_id) data from the given Model indicated by mod and id. """
    Model = mod_lookup(mod)
    model = Model.query.get(id)
    sheet = update_sheet(model, id=sheet_id)
    return render_template('data.html', mod=mod, id=id, sheet=sheet)


@app.route('/data/permissions/<string:mod>/<int:id>/<string:sheet_id>', methods=['GET', 'POST'])
@staff_required()
def data_permissions(mod, id, sheet_id, perm_id=None):
    """Used for managing permissions for who has access to a worksheet """
    app.logger.info(f'===== {mod} data permissions for sheet {sheet_id} ====')
    template = 'form_permission.html'
    sheet = perm_list(sheet_id)
    data = next((x for x in sheet.get('permissions', []) if x.id == perm_id), {}) if perm_id else {}
    action = 'Edit' if perm_id else 'Add'
    app.logger.debug(f'-------- {mod} Sheet {action} Permissions --------')
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        if action == 'Edit':
            # TODO: Manage updating the sheet permissions
            # model = db_update(data, id, Model=Model)
            pass
        else:  # action == 'Add'
            sheet = perm_add(sheet_id, data)
        return render_template('data.html', mod=mod, id=id, sheet=sheet)
    return render_template(template, mod=mod, id=id, action=action, data=data, sheet=sheet)


# ############# End Worksheets #############
# ############# Used for Facebook login, including onboarding. #############

@app.route('/login/<string:mod>')
def fb_login(mod):
    """Initiate the creation of a new Influencer or Brand, as indicated by 'mod' """
    app.logger.info(f'====================== NEW {mod} Account =========================')
    if app.config.get('LOCAL_ENV') is True:
        app.logger.error("Can not call the Facebook auth function when running locally. ")
        flash("This does not work when running locally. Redirecting to the home page. ")
        return redirect(url_for('home'))
    authorization_url = onboard_login(mod)
    return redirect(authorization_url)


@app.route('/callback/<string:mod>')
def callback(mod):
    """Handle the callback for Facebook authorization. Create new influencer or brand user as indicated by 'mod'. """
    app.logger.info(f'================= Authorization Callback {mod}===================')
    view, data = onboarding(mod, request)
    if view == 'decide':
        data = prep_ig_decide(data)
        return render_template('decide_ig.html', mod=mod, view=view, ig_list=data)  # POST to edit
    elif view == 'existing':
        app.logger.info("Login Existing influencer or brand user. ")
        app.logger.debug(f"Amongst these existing User options: {data}. ")
        return render_template('decide_ig.html', mod=mod, view=view, ig_list=data)  # POST to login_sel
    elif view == 'not_found':
        return render_template('decide_ig.html', mod=mod, view=view, ig_list=data)  # POST to edit, but no form.
    elif view == 'complete':
        app.logger.info("Completed User")
        return redirect(url_for('view', mod=mod, id=data[0].get('account_id')))
    elif view == 'error':
        return redirect(url_for('error', data=data), code=307)
    else:
        return redirect(url_for('error', data='unknown response'), code=307)


@app.route('/<string:mod>/<int:id>/login_select', methods=['GET', 'POST'])
@login_required
def login_sel(mod, id):
    """An influencer or brand is logging in with an existing user account. """
    user = User.query.get(id)
    message, url = '', url_for('home')
    if not user:
        message = "Selected a non-existent user. You are logged off. "
    elif user.facebook_id != current_user.facebook_id:
        message = "Not valid input. You are logged off. "
    elif user.role != mod:  # TODO: Should this be handled differently?
        txt = "Selected User does not match the selected mod. "
        app.logger.error(txt)
        flash(txt)
    logout_user()
    if message:
        app.logger.error(message)
        flash(message)
    else:
        login_user(user, force=True, remember=True)
        url = url_for('view', mod=user.role, id=user.id)
    return redirect(url)


@app.route('/<string:mod>/<int:id>/decide_new')
@login_required
def decide_new(mod, id):
    """An existing user is making an influencer or brand account with a different IG account. """
    from .api import onboard_new

    valid_mod = {'influencer', 'brand'}
    user = User.query.get(id)
    if mod not in valid_mod or not user or user != current_user:
        app.logger.error(f"Unable to decide_new for {mod}. ")
        flash(f"That feature for {mod} is not available at this time. Contact an Admin for details. ")
        return redirect(request.referrer)
    fb_id = getattr(user, 'facebook_id', '')
    data = {'facebook_id': fb_id, 'role': mod, 'token_expires': getattr(user, 'token_expires', None)}
    data['id'] = fb_id  # TODO: Remove once confirmed always looking for 'facebook_id' key instead.
    token = getattr(user, 'token', None)
    if not token:
        app.logger.info("User probably closed window/session. Starting over with login. ")
        # TODO: Check for potential infinate loop issues.
        return redirect(url_for('fb_login', mod=mod))
    view, data = onboard_new(data, token=token)  # ('not_found', data) | ('decide', data)
    if view == 'error':
        return redirect(url_for('error', data=data), code=307)
    if view == 'decide':
        data = prep_ig_decide(data)
    return render_template('decide_ig.html', mod=mod, view=view, ig_list=data)


# ############# End Facebook login functions. #############
# ########## The following are for Campaign Views ############


@app.route('/campaign/<int:id>/results', methods=['GET', 'POST'])
@staff_required()
def results_campaign(id):
    """Campaign Results View (on GET) or generate Worksheet report (on POST) """
    view, mod, related = 'results', 'campaign', {}
    template = f"{view}_{mod}.html"
    campaign = Campaign.query.get(id)
    if request.method == 'POST':
        sheet = create_sheet(campaign)
        app.logger.info(f"==== Campaign {view} Create Sheet ====")
        return render_template('data.html', mod=mod, id=id, sheet=sheet)
    app.logger.info(f'=========== Campaign {view} ===========')
    related = campaign.get_results()
    return render_template(template, mod=mod, view=view, data=campaign, related=related)


@app.route('/campaign/<int:id>/rejected', methods=['GET', 'POST'])
@staff_required()
def rejected_campaign(id):
    """For a given Campaign, show rejected posts (processed but not accepted posts). """
    return campaign(id, view='rejected')


@app.route('/campaign/<int:id>/detail', methods=['GET', 'POST'])
@staff_required()
def detail_campaign(id):
    """For a given Campaign, show posts accepted as part of the Campaign. """
    return campaign(id, view='collected')


@app.route('/campaign/<int:id>', methods=['GET', 'POST'])
@staff_required()
def campaign(id, view='management'):
    """Various views of media post lists for assigning, re-assessing, or preparing worksheets for campaigns.
    When view is 'management' (default), user can assign or reject posts for the campaign.
    When view is 'collected', user can review and re-assess posts already assigned to the campaign.
    When view is 'rejected', user can re-assess posts previously marked as rejected.
    On POST, updates the assigned media posts as indicated by the submitted form.
    """
    mod = 'campaign'
    template, related = f"{mod}.html", {}
    campaign = Campaign.query.get(id)
    app.logger.info(f'=========== Campaign {view} ===========')
    if request.method == 'POST':
        success = update_campaign(campaign, request)
        if not success:
            info = "Update Campaign Failed. "
            app.logger.error(info)
            flash(info)
    related = campaign.related_posts(view)
    return render_template(template, mod=mod, view=view, data=campaign, related=related, caption_errors=caption_errors)


@app.route('/campaign/<int:id>/update', methods=['GET'])
@staff_required()
def update_campaign_metrics(id):
    """Update the metrics for all posts assigned to a given Campaign. """
    camp = Campaign.query.get(id)
    prep_data = camp.prep_metrics_update()
    post_data = [get_metrics_media(media, facebook, metrics) for media, facebook, metrics in prep_data]
    count, success = media_posts_save(post_data, create_or_update='update')
    if success:
        info = f"Updated metrics for {count} non-story media posts. "
    else:
        info = "There was a problem with updating non-story media post metrics. Please contact an Admin. "
    flash(info)
    return redirect(request.referrer)


# ########## End of Campaign Views ############
# ########## Backend Routes: Used by Cron and Queue Tasks (possibly called by admin). ############


@app.route('/all_posts')
def all_posts():
    """Used for daily downloads, or can be called manually by an admin (but not managers). """
    app.logger.debug("===================== All Posts Process Run =====================")
    cron_run = request.headers.get('X-Appengine-Cron', None)
    if not cron_run:
        if not current_user.is_authenticated and current_user.role == 'admin':
            message = "This is not a valid user route. Contact an Admin to help resolve this problem. "
            flash(message)
            app.logger.error(message)
            return redirect(url_for('error'))
    all_ig = get_daily_ig_accounts()
    media_results = get_media_lists(all_ig)
    count, success = media_posts_save(media_results, add_time=True)
    message = f"For {len(all_ig)} users, got {count} posts. Initial save: {success}. "
    if success and count > 0:
        task_list = add_to_collect(media_results, queue_name='basic-post', in_seconds=180)
        success = all(ea is not None for ea in task_list)
    status = 201 if success else 500
    response = {'User_num': len(all_ig), 'Post_num': count, 'message': message, 'status_code': status}
    if cron_run:
        response = json.dumps(response)
    else:  # Process run by an admin.
        message += "Admin requested getting posts for all active users. "
        flash(message)
        response = redirect(url_for('admin', data=response))
    app.logger.info(message)
    return response


@app.route('/capture/report/', methods=['GET', 'POST'])
def capture_report():
    """After the capture work is processed, the results are sent here to update the models. """
    app.logger.info("======================== capture report route =============================")
    message = ''
    # pprint(request.headers)
    # TODO: Check request.headers or source info for signs this came from a task queue, and reject if not a valid source
    data = request.json if request.is_json else request.data
    data = json.loads(data.decode())
    # # data = {'success': Bool, 'message': '', 'source': {}, 'error': <answer remains>, 'changes':[change_vals, ...]}
    # # data['changes'] is a list of dict to be used as update content.
    app.logger.info('------------------  Source  -------------------------------------')
    pprint(data.get('source'))
    app.logger.info('------------------ Message  -------------------------------------')
    message += data.get('message')
    app.logger.info(message)
    if data.get('success', False) is False:
        app.logger.info('------------------ Answer Remains -------------------------------------')
        pprint(data.get('error'))
        return message, 500
    mod = data.get('source', {}).get('object_type', '')
    Model = mod_lookup(mod)
    return report_update(data.get('changes', []), Model)


@app.route('/collect/<string:mod>/<string:process>', methods=['GET', 'POST'])
def collect_queue(mod, process):
    """For backend handling requests for media post data from the Graph API with google cloud tasks. """
    known_process = ('basic', 'metrics', 'data')
    app.logger.debug(f"==================== collect queue: {mod} {process} ====================")
    if mod != 'post' or process not in known_process:
        return "Unknown Data Type or Process in Request", 404
    head = {}
    head['x_queue_name'] = request.headers.get('X-AppEngine-QueueName', None)
    head['x_task_id'] = request.headers.get('X-Appengine-Taskname', None)
    head['x_retry_count'] = request.headers.get('X-Appengine-Taskretrycount', None)
    head['x_response_count'] = request.headers.get('X-AppEngine-TaskExecutionCount', None)
    head['x_task_eta'] = request.headers.get('X-AppEngine-TaskETA', None)
    head['x_task_previous_response'] = request.headers.get('X-AppEngine-TaskPreviousResponse', None)
    head['x_task_retry_reason'] = request.headers.get('X-AppEngine-TaskRetryReason', None)
    head['x_fail_fast'] = request.headers.get('X-AppEngine-FailFast', None)
    req_body = request.json if request.is_json else request.data
    if not head['x_queue_name'] or not head['x_task_id']:
        app.logger.error("This request is not coming from our project. It should be rejected. ")
        return "Unknown Request", 404
    if not req_body:
        return "No request body. ", 404
    req_body = json.loads(req_body.decode())  # The request body from a Task API is byte encoded
    source = req_body.get('source', {})
    source.update(head)
    app.logger.debug("------------------------ SOURCE ------------------------")
    app.logger.debug(source)
    dataset = req_body.get('dataset', [])
    user_id = dataset.get('user_id', 'NOT FOUND')
    media_count = len(dataset.get('media_list', []))
    app.logger.debug(f"------------------------ Media: {media_count} for User ID: {user_id} ------------------------")
    result = handle_collect_media(dataset, process)
    if isinstance(result, list):
        count, success = media_posts_save(result, create_or_update='update')
        if success:
            info = f"Updated {count} Post records with media {process} info for user ID: {user_id} - SUCCESS. "
            app.logger.debug(info)
            result = {'reason': info, 'status_code': 201}
        else:
            info = f"Updating {count} Posts with the media {process} results for user ID: {user_id} - FAILED. "
            app.logger.error(info)
            result = {'error': info, 'status_code': 500}
    status_code = 500 if 'error' in result else 201
    status_code = result.pop('status_code', status_code)
    return result, status_code


@app.route('/post/hook/', methods=['GET', 'POST'])
def hook():
    """Endpoint receives all webhook updates from Instagram/Facebook for Story Posts. """
    app.logger.debug(f"========== The hook route has a {request.method} request ==========")
    if request.method == 'POST':
        signed = request.headers.get('X-Hub-Signature', '')
        data = request.json if request.is_json else request.data  # request.get_data() for byte_data
        verified = check_hash(signed, data)
        if not verified:
            message = "Signature given for webhook could not be verified. "
            app.logger.error(message)
            return message, 401  # 403 if we KNOW it was done wrong
        res, response_code = process_hook(data)
    else:  # request.method == 'GET':
        mode = request.args.get('hub.mode')
        token_match = request.args.get('hub.verify_token', '') if request.args.get('hub.mode') == 'subscribe' else ''
        token_match = True if token_match == app.config.get('FB_HOOK_SECRET') else False
        res = request.args.get('hub.challenge', '') if token_match else 'Error. '
        response_code = 200 if token_match else 401
        app.logger.debug(f"Mode: {mode} | Challenge: {res} | Token: {token_match} ")
    app.logger.debug(f"==================== The hook route returns status code: {response_code} ====================")
    app.logger.debug(res)
    return res, response_code


# ########## End of Backend Routes ############
# ########## User Updates and Views: Show or collect from the Graph API data for users. ############

@app.route('/<string:mod>/<int:id>/insights')
@login_required
def insights(mod, id):
    """For a given User (influencer or brand), show the account Insight data. """
    return_path = redirect(request.referrer)
    error_message = ''
    if mod not in ('influencer', 'brand'):
        error_message = "Invalid user role or type to collect new posts. "
    if current_user.role not in ['admin', 'manager'] and current_user.id != id:
        error_message += "This was not a correct location. You are redirected to the home page. "
    if error_message:
        flash(error_message)
        return return_path
    user = db_read(id)
    scheme_color = ['gold', 'purple', 'green', 'blue']
    dataset, i = {}, 0
    max_val, min_val = 4, float('inf')

    for metrics in (Insight.INFLUENCE_METRICS, Insight.PROFILE_METRICS, OnlineFollowers.METRICS):
        for metric in metrics:
            # TODO: Undo the following temporary ignore a lot of the metrics
            if metric in ('impressions', 'reach', 'profile_views'):
                if metrics == OnlineFollowers.METRICS:
                    query = OnlineFollowers.query.filter_by(user_id=id).order_by('recorded', 'hour').all()
                    if len(query):
                        temp_data = {(ea.recorded.strftime("%d %b, %Y"), int(ea.hour)): int(ea.value) for ea in query}
                    else:
                        temp_data = {'key1': 1, 'key2': 0}
                else:
                    query = Insight.query.filter_by(user_id=id, name=metric).order_by('recorded').all()
                    temp_data = {ea.recorded.strftime("%d %b, %Y"): int(ea.value) for ea in query}
                max_curr = max(*temp_data.values())
                min_curr = min(*temp_data.values())
                max_val = max(max_val, max_curr)
                min_val = min(min_val, min_curr)
                chart = {
                    'label': metric,
                    'backgroundColor': scheme_color[i % len(scheme_color)],
                    'borderColor': '#214',
                    'data': list(temp_data.values())
                }
                temp = {'chart': chart, 'data_dict': temp_data, 'max': max_curr, 'min': min_curr}
                dataset[metric] = temp
                i += 1
    kwargs = {'dataset': dataset}
    kwargs['user'] = user['name']
    kwargs['labels'] = [ea for ea in dataset['reach']['data_dict'].keys()]
    kwargs['max_val'] = int(1.2 * max_val)
    kwargs['min_val'] = int(0.8 * min_val)
    kwargs['steps'] = len(kwargs['labels']) // 25  # TODO: Update steps as appropriate for the metric / chart.
    # return render_template('chart.html', user=user['name'], dataset=, labels=, max=max_val, min=min_val, steps=steps)
    return render_template('chart.html', **kwargs)


@app.route('/<string:mod>/<int:id>/audience')
@login_required
def new_audience(mod, id):
    """Get new audience data from API for either. Input mod for either User or Brand, with given id. """
    if current_user.role not in ['admin', 'manager'] and current_user.id != id:
        flash("This was not a correct location. You are redirected to the home page. ")
        return redirect(url_for('home'))
    audience = get_audience(id)
    logstring = f"New Audience data for {mod} - {id}. " if audience else f"No audience insight data, {mod}. "
    app.logger.info(logstring)
    flash(logstring)
    return redirect(url_for('view', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/followers')
@login_required
def followers(mod, id):
    """Get 'online_followers' report """
    if current_user.role not in ['admin', 'manager'] and current_user.id != id:
        flash("This was not a correct location. You are redirected to the home page. ")
        return redirect(url_for('home'))
    follow_report = get_online_followers(id)
    logstring = "New Online Followers for {mod} - {id}. " if follow_report else "No new Online Followers data. "
    app.logger.info(logstring)
    flash(logstring)
    return redirect(url_for('view', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/fetch')
@login_required
def new_insight(mod, id):
    """Get new account insight data from API. Input mod for either User or Brand, with given id. """
    if current_user.role not in ['admin', 'manager'] and current_user.id != id:
        flash("This was not a correct location. You are redirected to the home page. ")
        return redirect(url_for('home'))
    insights, follow_report = get_insight(id)
    logstring = f"For {mod} - {id}: "
    logstring += "New Insight data added. " if insights else "No new insight data found. "
    logstring += "New Online Followers data added. " if follow_report else "No new online followers data found. "
    app.logger.info(logstring)
    flash(logstring)
    return redirect(url_for('insights', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/posts')
@login_required
def new_post(mod, id):
    """Get new posts data from API for a given user. Input mod for either User or Brand, with a given id. """
    return_path = redirect(request.referrer)
    error_message = ''
    if mod not in ('influencer', 'brand'):
        error_message = "Invalid user role or type to collect new posts. "
    if current_user.role not in ['admin', 'manager'] and current_user.id != id:
        error_message += "You do not have permissions for that action. No updates made. "
    if error_message:
        flash(error_message)
        return return_path
    media_results = get_media_lists(id, only_ids=False)
    found = len(media_results[0].get('media_list', [])) if media_results else 0
    logstring = f"Found {found} media posts. "
    count, success = media_posts_save(media_results, add_time=False)
    logstring += f"Saved {count} new Posts. " if success else "No new posts were saved. "
    app.logger.debug(logstring)
    flash(logstring)
    return return_path


# ########## End User Updates and Views ############
# ########## The following are for general Views ############


@app.route('/<string:mod>/<int:id>')
@login_required
def view(mod, id):
    """Used primarily for specific User or Brand views, but also any data model view except Campaign. """
    # if mod == 'campaign':
    #     return campaign(id)
    Model, model = mod_lookup(mod), None
    if current_user.role not in ['manager', 'admin']:
        if mod in User.ROLES:
            if current_user.role == mod and current_user.id != id:
                flash("Incorrect location. You are being redirected to your own profile page. ")
                return redirect(url_for('view', mod=current_user.role, id=current_user.id))
        elif mod in ['post', 'audience']:
            # The user can only view this detail view if they are associated to the data
            model = Model.query.get(id)
            if model.user != current_user:
                flash("Incorrect location. You are being redirected to the home page. ")
                return redirect(url_for('home'))
        else:
            flash("This was not a correct location. You are being redirected to the home page. ")
            return redirect(url_for('home'))
    model = model or Model.query.get(id)
    template = 'view.html'
    if mod == 'post':
        template = f"{mod}_{template}"
        model = model.display()
    else:
        model = from_sql(model, related=True, safe=True)
        related_user = from_sql(model.user, related=False, safe=True) if getattr(model, 'user', None) else None
        if mod == 'insight':
            template = f"{mod}_{template}"
            model['user'] = related_user
        elif mod == 'audience':
            template = f"{mod}_{template}"
            model['user'] = related_user
            value = json.loads(model['value'])
            if not isinstance(value, dict):  # For the id_data Audience records
                value = {'value': value}
            model['value'] = value
    # TODO: Remove these temporary logs
    # app.logger.info(f"Current User: {current_user} ")
    return render_template(template, mod=mod, data=model, caption_errors=caption_errors)


@app.route('/<string:mod>/add', methods=['GET', 'POST'])
@staff_required()
def add(mod):
    """For a given data Model, as indicated by mod, add new data to DB. """
    valid_mod = {'campaign', 'brand'}
    if mod not in valid_mod:
        app.logger.error(f"Unable to add {mod}. ")
        flash(f"Adding a {mod} is not working right now. Contact an Admin. ")
        return redirect(request.referrer)
    return add_edit(mod, id=None)


@app.route('/<string:mod>/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(mod, id):
    """Modify the existing DB entry. Model indicated by mod, and provided record id. """
    valid_mod = {'campaign'}.union(User.ROLES)
    if mod not in valid_mod:
        app.logger.error(f"Unable to edit {mod}. ")
        flash(f"Editing a {mod} is not working right now. Contact an Admin. ")
        return redirect(request.referrer)
    if current_user.role not in ['admin', 'manager'] and (current_user.id != id or current_user.role != mod):
        app.logger.info(f"Error in edit route | mod: {mod} | id: {id} | current_user: {current_user} ")
        flash("Something went wrong. Contact an admin or manager. Redirecting to the home page. ")
        return redirect(url_for('home'))
    return add_edit(mod, id=id)


@app.route('/<string:mod>/<int:id>/delete', methods=['GET', 'POST'])
@login_required
def delete(mod, id):
    """Permanently remove from DB the record for Model indicated by mod and id. """
    if current_user.role not in ['admin', 'manager'] and (current_user.id != id or current_user.role != mod):
        message = "Something went wrong. Can not delete. Contact an admin or manager. "
        flash(message)
        return redirect(request.referrer)
    Model = mod_lookup(mod)
    if request.method == 'POST':
        confirm = True if request.form.get('confirm') == 'yes' else False
        if not confirm:
            flash(f"{mod.capitalize()} was not deleted. ")
            return redirect(request.form.get('next') or request.referrer)
        try:
            db_delete(id, Model=Model)
            flash('The deletion is complete')
        except Exception as e:
            message = f"We were unable to delete {mod} - {Model} - {id}. "
            app.logger.error(message)
            app.logger.exception(e)
            flash(message)
            return redirect(request.form.get('next') or request.referrer)
        return redirect(url_for('home'))
    model = db_read(id, related=False, Model=Model)
    return render_template('delete_confirm.html', data=model, next=request.referrer)


@app.route('/<string:mod>/list')
@login_required
def list_all(mod):
    """List view for all data of Model, or Google Drive Files, as indicated by mod.
    The list view for influencer and brand will redirect those user types to their profile.
    Only admin & manager users can see these list views for brands, influencers, or campaigns.
    Other list views may be available depending on the user.role, but admin users can see all list views.
    """
    if current_user.role not in ['admin', 'manager']:
        if mod in User.ROLES:
            if current_user.role == mod:
                return redirect(url_for('view', mod=mod, id=current_user.id))
            elif mod in ['influencer', 'brand']:
                flash(f"Did you click the wrong link? You are not a {mod} user. ")
                flash(f"Or did you want to join the platform as a {mod}, using a different Instagram account? ")
                return redirect(url_for('signup'))
        flash("It seems that is not a correct route. You are redirected to the home page. ")
        return redirect(url_for('home'))
    view = None  # Possible values: 'all', 'active', 'Not Active', 'completed', None
    if mod == 'file':
        models = all_files()
    else:
        Model = mod_lookup(mod)
        role = mod if Model == User else request.args.get('role', None)  # 'all', 'completed', ...
        view = request.args.get('view', None)
        if Model == Campaign:
            view = role or 'active'
        models = db_all(Model=Model, role=role) if Model in (User, Campaign) else db_all(Model=Model)
        if view and Model == User and view != 'all':
            active_opt = True if view == 'active' else False
            models = [ea for ea in models if ea.has_active_all is active_opt]
    return render_template('list.html', mod=mod, data=models, view=view)


# Catchall redirect route.
@app.route('/<string:page_name>/')
def render_static(page_name):
    """Catch all for undefined routes. Return the requested static page. """
    if page_name in ('favicon.ico', 'robots.txt'):
        return redirect(url_for('static', filename=page_name))
    page_name += '.html'
    return render_template(page_name)
