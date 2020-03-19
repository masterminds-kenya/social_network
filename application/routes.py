from flask import current_app as app
from flask import render_template, redirect, url_for, request, flash  # , abort
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from .model_db import db_create, db_read, db_update, db_delete, db_all, from_sql
from .model_db import User, OnlineFollowers, Insight, Audience, Post, Campaign  # , metric_clean
from . import developer_admin
from functools import wraps
from .manage import update_campaign, process_form
from .api import onboard_login, onboarding, get_insight, get_audience, get_posts, get_online_followers
from .sheets import create_sheet, update_sheet, perm_add, perm_list, all_files
import json
from pprint import pprint


def mod_lookup(mod):
    """ Associate to the appropriate Model, or raise error if 'mod' is not an expected value """
    if not isinstance(mod, str):
        raise TypeError('Expected a string input')
    lookup = {'insight': Insight, 'audience': Audience, 'post': Post, 'campaign': Campaign}
    # 'onlinefollowers': OnlineFollowers,
    lookup.update({role: User for role in User.roles})
    Model = lookup.get(mod, None)
    if not Model:
        raise ValueError('That is not a valid url path.')
    return Model


def staff_required(role=['admin', 'manager']):
    """ This decorator will allow use to limit access to routes based on user role. """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in role:
                return app.login_manager.unauthorized()
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


def admin_required(role=['admin']):
    """ This decorator will limit access to admin only """
    # staff_required(role=role)
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in role:
                return app.login_manager.unauthorized()
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


# def self_or_staff_required(role=['admin', 'manager']):
#     """ This decorator limits access to staff or if the resource belongs to the current_user. """
#     def wrapper(fn):
#         @wraps(fn)
#         def decorated_view(*args, **kwargs):
#             if not current_user.is_authenticated or current_user.role not in role:
#                 return app.login_manager.unauthorized()
#             return fn(*args, **kwargs)
#         return decorated_view
#     return wrapper


@app.route('/')
def home():
    """ Default root route """
    data = ''
    return render_template('index.html', data=data)


@app.route('/deletion')
def fb_delete():
    """ Handle a Facebook Data Deletion Request
        More details: https://developers.facebook.com/docs/apps/delete-data
        Not yet implemented.
    """
    response = {}
    response['user_id'] = 'test user_id'
    response['url'] = 'see status of deletion'
    response['confirmation_code'] = 'some unique code'
    # do stuff
    return json.dumps(response)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """ Using Flask-Login to create a new user (manager or admin) account """
    app.logger.info(f'--------- Sign Up User ------------')
    ignore = ['influencer', 'brand']
    signup_roles = [role for role in User.roles if role not in ignore]
    if request.method == 'POST':
        mod = request.form.get('role')
        if mod not in signup_roles:
            raise ValueError("That is not a valid role selection")
        data = process_form(mod, request)
        password = data.get('password', None)
        # TODO: allow system for an admin to create a user w/o a password,
        # but require that user to create a password on first login
        admin_create = False
        if not password and not admin_create:
            flash("A password is required.")
            return redirect(url_for('signup'))
        else:
            data['password'] = generate_password_hash(password)
        user = User.query.filter_by(name=data['name']).first()
        if user:
            flash("That name is already in use.")
            return redirect(url_for('signup'))
        user = User.query.filter_by(email=data['email']).first()
        if user:
            flash("That email address is already in use.")
            return redirect(url_for('signup'))
        user = db_create(data)
        flash("You have created a new user account!")
        return redirect(url_for('view', mod=mod, id=user['id']))

    next_page = request.args.get('next')
    if next_page == url_for('all', mod='influencer'):
        mods = ['influencer']
    elif next_page == url_for('all', mod='brand'):
        mods = ['brand']
    else:
        mods = ['influencer', 'brand']
    return render_template('signup.html', signup_roles=signup_roles, mods=mods)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """ This the the manual login process. """
    if request.method == 'POST':
        data = process_form('login', request)
        password = data.get('password', None)
        if not password:
            flash("A password is required.")
            return redirect(url_for('login'))
        user = User.query.filter_by(email=data['email']).first()
        if not user or not check_password_hash(user.password, data['password']):
            flash("Those login details did not work.")
            return redirect(url_for('login'))
        login_user(user, remember=data['remember'])
        return redirect(url_for('view', mod=user.role, id=user.id))
    return render_template('signup.html', signup_roles=[], mods=['influencer', 'brand'])


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You are now logged out.")
    return redirect(url_for('home'))


@app.route('/error', methods=['GET', 'POST'])
def error():
    err = request.form.get('data')
    app.logger.error(err)
    return render_template('error.html', err=err)


@app.route('/admin')
@admin_required()
def admin(data=None):
    """ Platform Admin view to view links and actions unique to admin """
    dev_email = ['hepcatchris@gmail.com', 'christopherlchapman42@gmail.com']
    dev = current_user.email in dev_email
    # files = None if app.config.get('LOCAL_ENV') else all_files()
    files = None
    return render_template('admin.html', dev=dev, data=data, files=files)


@app.route('/data/load/')
@admin_required()
def load_user():
    """ This is a temporary development function. Will be removed for production. """
    developer_admin.load()
    return redirect(url_for('all', mod='influencer'))


@app.route('/data/<string:mod>/<int:id>')
@admin_required()
def backup_save(mod, id):
    """ This is a temporary development function. Will be removed for production. """
    Model = mod_lookup(mod)
    count = developer_admin.save(mod, id, Model)
    message = f"We just backed up {count} {mod} model(s)"
    app.logger.info(message)
    flash(message)
    return redirect(url_for('view', mod='influencer', id=id))


@app.route('/data/encrypt/')
@admin_required()
def encrypt():
    """ This is a temporary development function. Will be removed for production. """
    from .model_db import db

    message, count = '', 0
    users = User.query.all()
    try:
        for user in users:
            value = getattr(user, 'token')
            app.logger.debug(value)
            setattr(user, 'crypt', value)
            count += 1
        message += f"Adjusted for {count} users. "
        db.session.commit()
        message += "Commit Finished! "
    except error as e:
        temp = f"Encrypt method error. Count: {count}. "
        app.logger.error(temp)
        app.logger.exception(e)
        message += temp
        db.session.rollback()
    flash(message)
    app.logger.info(message)
    return redirect(url_for('admin'))


# ########## The following are for worksheets ############


@app.route('/<string:mod>/<int:id>/export', methods=['GET', 'POST'])
@staff_required()
def export(mod, id):
    """ Export data to google sheet, generally for influencer or brand Users.
        Was view results on GET and generate Sheet on POST .
    """
    app.logger.info(f"==== {mod} Create Sheet ====")
    Model = mod_lookup(mod)
    model = Model.query.get(id)
    sheet = create_sheet(model)
    return render_template('data.html', mod=mod, id=id, sheet=sheet)


@app.route('/data/update/<string:mod>/<int:id>/<string:sheet_id>')
@staff_required()
def update_data(mod, id, sheet_id):
    """ Update the given worksheet (sheet_id) data from the given Model indicated by mod and id. """
    Model = mod_lookup(mod)
    model = Model.query.get(id)
    sheet = update_sheet(model, id=sheet_id)
    return render_template('data.html', mod=mod, id=id, sheet=sheet)


@app.route('/data/permissions/<string:mod>/<int:id>/<string:sheet_id>', methods=['GET', 'POST'])
@staff_required()
def data_permissions(mod, id, sheet_id, perm_id=None):
    """ Used for managing permissions for who has access to a worksheet """
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

@app.route('/login/<string:mod>')
def fb_login(mod):
    """ Initiate the creation of a new Influencer or Brand, as indicated by 'mod' """
    app.logger.info(f'====================== NEW {mod} Account =========================')
    if app.config.get('LOCAL_ENV') is True:
        app.logger.error('Can not call the Facebook auth function when running locally')
        flash('This does not work when running locally. Redirecting to the home page.')
        return redirect(url_for('home'))
    authorization_url = onboard_login(mod)
    return redirect(authorization_url)


@app.route('/callback/<string:mod>')
def callback(mod):
    """ Handle the callback for Facebook authorization. Create new influencer or brand user as indicated by 'mod'. """
    app.logger.info(f'================= Authorization Callback {mod}===================')
    view, data, account_id = onboarding(mod, request)
    if view == 'decide':
        app.logger.info(f"Decide which IG account | Data: {data} | ID: {account_id} ")
        ig_list = []
        for ig_info in data:
            cleaned = {}
            for key, value in ig_info.items():
                cleaned[key] = json.dumps(value) if key in Audience.ig_data else value
            ig_list.append(cleaned)
        app.logger.debug(f"Amongst these IG options: {ig_list}")
        return render_template('decide_ig.html', mod=mod, id=account_id, ig_list=ig_list)
    elif view == 'complete':
        app.logger.info(f"Completed User")
        return redirect(url_for('view', mod=mod, id=account_id))
    elif view == 'error':
        return redirect(url_for('error', data=data), code=307)
    else:
        return redirect(url_for('error', data='unknown response'), code=307)

# ########## The following are for Campaign Views ############


@app.route('/campaign/<int:id>/results', methods=['GET', 'POST'])
@staff_required()
def results(id):
    """ Campaign Results View (on GET) or generate Worksheet report (on POST) """
    mod, view = 'campaign', 'results'
    template, related = f"{view}_{mod}.html", {}
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
    """ For a given Campaign, show rejected posts (processed but not accepted posts). """
    return campaign(id, view='rejected')


@app.route('/campaign/<int:id>/detail', methods=['GET', 'POST'])
@staff_required()
def detail_campaign(id):
    """ For a given Campaign, show posts accepted as part of the Campaign. """
    return campaign(id, view='collected')


@app.route('/campaign/<int:id>', methods=['GET', 'POST'])
@staff_required()
def campaign(id, view='management'):
    """ Defaults to management of assigning posts to a campaign.
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
            app.logger.error("Update Campaign Failed")
    for user in campaign.users:
        if view == 'management':
            related[user] = user.campaign_unprocessed(campaign)
        elif view == 'collected':
            related[user] = user.campaign_posts(campaign)
        elif view == 'rejected':
            related[user] = user.campaign_rejected(campaign)
        else:
            related[user] = []  # This condition should not occur.
    return render_template(template, mod=mod, view=view, data=campaign, related=related)

# ########## End of Campaign Views ############
# ########## The following are for general Views ############


@app.route('/all_posts')
def all_posts():
    app.logger.info("===================== All Posts Process Run =====================")
    cron_run = request.headers.get('X-Appengine-Cron', None)
    admin_run = request.referrer == url_for('admin')
    if not cron_run and not admin_run:
        app.logger.error('All posts was run by something other than cron job or admin link')
        return redirect(url_for('error'))
    all_ig = User.query.filter(User.instagram_id.isnot(None)).all()
    for ea in all_ig:
        get_posts(ea.id)
    message = f"Got all posts for {len(all_ig)} accounts. "
    if admin_run:
        message += "Admin requested getting posts for all users. "
        flash(message)
        return_path = url_for('admin')
    elif cron_run:
        message += "Cron job completed"
        return_path = url_for('home')  # TODO: Check expected response on success / completion.
    app.logger.info(message)
    return redirect(return_path)


@app.route('/<string:mod>/<int:id>')
@login_required
def view(mod, id):
    """ Used primarily for specific User or Brand views, but also any data model view except Campaign. """
    # if mod == 'campaign':
    #     return campaign(id)
    Model, model = None, None
    if current_user.role not in ['manager', 'admin']:
        if mod in User.roles:
            if current_user.role == mod and current_user.id != id:
                flash('Incorrect location. You are being redirected to your own profile page')
                return redirect(url_for('view', mod=current_user.role, id=current_user.id))
        elif mod in ['post', 'audience']:
            # The user can only view this detail view if they are associated to the data
            Model = mod_lookup(mod)
            model = Model.query.get(id)
            if model.user != current_user:
                flash('Incorrect location. You are being redirected to the home page.')
                return redirect(url_for('home'))
        else:
            flash('This was not a correct location. You are redirected to the home page.')
            return redirect(url_for('home'))
    Model = Model or mod_lookup(mod)
    model = model or Model.query.get(id)
    related_user = from_sql(model.user, related=False, safe=True) if getattr(model, 'user', None) else None
    model = from_sql(model, related=True, safe=True)
    template = 'view.html'
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
    elif mod == 'post':
        template = f"{mod}_{template}"
        model = model.display()
    return render_template(template, mod=mod, data=model)


@app.route('/<string:mod>/<int:id>/insights')
@login_required
def insights(mod, id):
    """ For a given User (influencer or brand), show the account Insight data. """
    if current_user.role not in ['admin', 'manager'] and current_user.id != id:
        flash('This was not a correct location. You are redirected to the home page.')
        return redirect(url_for('home'))
    user = db_read(id)
    scheme_color = ['gold', 'purple', 'green', 'blue']
    dataset, i = {}, 0
    max_val, min_val = 4, float('inf')

    for metrics in (Insight.influence_metrics, Insight.profile_metrics, OnlineFollowers.metrics):
        for metric in metrics:
            # TODO: Undo the following temporary ignore a lot of the metrics
            if metric in ('impressions', 'reach', 'profile_views'):
                if metrics == OnlineFollowers.metrics:
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
    labels = [ea for ea in dataset['reach']['data_dict'].keys()]
    max_val = int(1.2 * max_val)
    min_val = int(0.8 * min_val)
    steps = len(labels) // 25  # TODO: Update steps as appropriate for the metric / chart.
    return render_template('chart.html', user=user['name'], dataset=dataset, labels=labels, max=max_val, min=min_val, steps=steps)


@app.route('/<string:mod>/<int:id>/audience')
@login_required
def new_audience(mod, id):
    """ Get new audience data from API for either. Input mod for either User or Brand, with given id. """
    if current_user.role not in ['admin', 'manager'] and current_user.id != id:
        flash('This was not a correct location. You are redirected to the home page.')
        return redirect(url_for('home'))
    audience = get_audience(id)
    logstring = f'New Audience data for {mod} - {id}' if audience else f'No audience insight data, {mod}'
    app.logger.info(logstring)
    flash(logstring)
    return redirect(url_for('view', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/followers')
@login_required
def followers(mod, id):
    """ Get 'online_followers' report """
    if current_user.role not in ['admin', 'manager'] and current_user.id != id:
        flash('This was not a correct location. You are redirected to the home page.')
        return redirect(url_for('home'))
    follow_report = get_online_followers(id)
    logstring = f"New Online Followers for {mod} - {id}" if follow_report else f"No new Online Followers data"
    app.logger.info(logstring)
    flash(logstring)
    return redirect(url_for('view', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/fetch')
@login_required
def new_insight(mod, id):
    """ Get new account insight data from API. Input mod for either User or Brand, with given id. """
    if current_user.role not in ['admin', 'manager'] and current_user.id != id:
        flash('This was not a correct location. You are redirected to the home page.')
        return redirect(url_for('home'))
    insights = get_insight(id)
    logstring = f'New Insight data for {mod} - {id} ' if insights else f'No new insight data found for {mod}'
    app.logger.info(logstring)
    flash(logstring)
    return redirect(url_for('insights', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/posts')
@login_required
def new_post(mod, id):
    """ Get new posts data from API. Input mod for either User or Brand, with a given id"""
    if current_user.role not in ['admin', 'manager'] and current_user.id != id:
        flash('This was not a correct location. You are redirected to the home page.')
        return redirect(url_for('home'))
    posts = get_posts(id)
    logstring = 'New Posts were retrieved. ' if len(posts) else 'No new posts were found. '
    app.logger.info(logstring)
    flash(logstring)
    return_path = request.referrer
    return redirect(return_path)


def add_edit(mod, id=None):
    """ Adding or Editing a DB record is a similar process handled here. """
    action = 'Edit' if id else 'Add'
    Model = mod_lookup(mod)
    if action == 'Add' and Model == User:
        if not current_user.is_authenticated \
           or current_user.role not in ['admin', 'manager'] \
           or mod != 'brand':
            flash("Using Signup")
            return redirect(url_for('signup'))
    app.logger.info(f'------- {action} {mod} ----------')
    if request.method == 'POST':
        data = process_form(mod, request)
        if mod == 'brand' and data.get('instagram_id', '') in ('None', ''):
            # TODO: Decide - Should it work for all User.roles, or only 'brand'?
            data['instagram_id'] = None  # Do not overwrite 'instagram_id' if it was left blank.
        # TODO: ?Check for failing unique column fields, or failing composite unique requirements?
        if action == 'Edit':
            password_mismatch = data.get('password', '') != data.get('password-confirm', '')
            if password_mismatch:
                message = "New password and its confirmation did not match. Please try again. "
                flash(message)
                return redirect(request.referrer)
            if Model == User and data.get('password'):
                # if form password field was blank, process_form has already removed the key by now.
                data['password'] = generate_password_hash(data.get('password'))
            try:
                model = db_update(data, id, Model=Model)
            except ValueError as e:
                app.logger.error('------- Came back as ValueError from Integrity Error -----')
                app.logger.exception(e)
                # Possibly that User account exists for the 'instagram_id'
                # If true, then switch to updating the existing user account
                #     and delete this newly created User account that was trying to be a duplicate.
                ig_id = data.get('instagram_id', None)
                found_user = User.query.filter_by(instagram_id=ig_id).first() if ig_id and Model == User else None
                if found_user:
                    found_user_id = getattr(found_user, 'id', None)
                    # TODO: Is the following check sufficient to block the security hole if Updating the 'instagram_id' field on a form
                    if current_user.facebook_id == found_user.facebook_id:
                        try:
                            model = db_update(data, found_user_id, Model=Model)
                        except ValueError as e:
                            message = 'Unable to update existing user'
                            app.logger.error(f'----- {message} ----')
                            app.logger.exception(e)
                            flash(message)
                            return redirect(url_for('home'))
                        login_user(found_user, force=True, remember=True)
                        flash('You are logged in.')
                        db_delete(id, Model=User)
                    else:
                        message = "You do not seem to match the existing account. "
                        message += "A new account can not be created with those unique values. "
                        message += "If you own the existing account you can try to Login instead. "
                else:
                    flash('Please try again or contact an Admin')
        else:  # action == 'Add'
            try:
                model = db_create(data, Model=Model)
            except ValueError as e:
                app.logger.error('------- Came back as ValueError from Integrity Error -----')
                app.logger.exception(e)
                flash('Error. Please try again or contact an Admin')
                return redirect(url_for('add', mod=mod, id=id))
        return redirect(url_for('view', mod=mod, id=model['id']))
    template, related = 'form.html', {}
    model = db_read(id, Model=Model) if action == 'Edit' else {}
    if mod == 'campaign':
        template = f"{mod}_{template}"
        users = User.query.filter_by(role='influencer').all()
        brands = User.query.filter_by(role='brand').all()
        related['users'] = [(ea.id, ea.name) for ea in users]
        related['brands'] = [(ea.id, ea.name) for ea in brands]
    return render_template(template, action=action, mod=mod, data=model, related=related)


@app.route('/<string:mod>/add', methods=['GET', 'POST'])
@staff_required()
def add(mod):
    """ For a given data Model, as indicated by mod, add new data to DB. """
    valid_mod = {'campaign', 'brand'}
    if mod not in valid_mod:
        app.logger.error(f"Unable to add {mod}")
        flash(f"Adding a {mod} is not working right now. Contact an Admin")
        return redirect(request.referrer)
    return add_edit(mod, id=None)


@app.route('/<string:mod>/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(mod, id):
    """ Modify the existing DB entry. Model indicated by mod, and provided record id. """
    valid_mod = {'campaign'}.union(set(User.roles))
    if mod not in valid_mod:
        app.logger.error(f"Unable to edit {mod}")
        flash(f"Editing a {mod} is not working right now. Contact an Admin")
        return redirect(request.referrer)
    if current_user.role not in ['admin', 'manager'] and (current_user.id != id or current_user.role != mod):
        flash('Something went wrong. Contact an admin or manager. Redirecting to the home page.')
        return redirect(url_for('home'))
    return add_edit(mod, id=id)


@app.route('/<string:mod>/<int:id>/delete', methods=['GET', 'POST'])
@login_required
def delete(mod, id):
    """ Permanently remove from DB the record for Model indicated by mod and id. """
    if current_user.role not in ['admin', 'manager'] and (current_user.id != id or current_user.role != mod):
        message = 'Something went wrong. Can not delete. Contact an admin or manager. '
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
def all(mod):
    """ List view for all data of Model, or Google Drive Files, as indicated by mod.
        Only admin & manager users are allowed to see the campaign list view.
        The list view for influencer and brand will redirect those user types to their profile.
        Otherwise, only admin & manager users can see these list views for brands or influencers.
        All other list views can only be seen by admin users.
    """
    if current_user.role not in ['admin', 'manager']:
        if mod in User.roles:
            if current_user.role == mod:
                return redirect(url_for('view', mod=mod, id=current_user.id))
            elif mod in ['influencer', 'brand']:
                flash(f"Did you click the wrong link? You are not a {mod} user.")
                flash(f"Or did you want to join the platform as a {mod}, using a different Instagram account?")
                return redirect(url_for('signup'))
        flash('It seems that is not a correct route. You are redirected to the home page.')
        return redirect(url_for('home'))
    if mod not in ['campaign', *User.roles] and current_user.role != 'admin':
        flash('It seems that is not a correct route. You are redirected to the home page.')
        return redirect(url_for('home'))
    if mod == 'file':
        models = all_files()
    else:
        Model = mod_lookup(mod)
        models = db_all(Model=Model, role=mod) if Model == User else db_all(Model=Model)
    return render_template('list.html', mod=mod, data=models)


# Catchall redirect route.
@app.route('/<string:page_name>/')
def render_static(page_name):
    """ Catch all for undefined routes. Return the requested static page. """
    page_name += '.html' if page_name != 'robots.txt' else ''
    return render_template(page_name)
