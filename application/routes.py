from flask import current_app as app
from flask import render_template, redirect, url_for, request, abort, flash
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from .model_db import db_create, db_read, db_update, db_delete, db_all
from .model_db import User, OnlineFollowers, Insight, Audience, Post, Campaign  # , metric_clean
from . import developer_admin
from functools import wraps
from .manage import update_campaign, process_form, post_display
from .api import onboard_login, onboarding, get_insight, get_audience, get_posts, get_online_followers
from .sheets import create_sheet, update_sheet, read_sheet, perm_add, perm_list, all_files
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


@app.route('/')
def home():
    """ Default root route """
    data = ''
    return render_template('index.html', data=data)


@app.route('/signup', methods=['GET', 'POST'])
def signup(add=None):
    """ Using Flask-Login to create a new user (manager or admin) account """
    app.logger.info(f'--------- Sign Up User ------------')
    ignore = ['influencer', 'brand']
    if current_user.is_authenticated and current_user.role not in ['admin', 'manager']:
        ignore.append('brand')
    signup_roles = [role for role in User.roles if role not in ignore]

    if request.method == 'POST':
        print('------- Post on Sign Up ---------')
        pprint(request.form)
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
            flash("That email is already in use.")
            return redirect(url_for('signup'))
        user = db_create(data)
        flash("You have created a new user account!")
        return redirect(url_for('view', mod=mod, id=user['id']))

    return render_template('signup.html', signup_roles=signup_roles)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """ This the the manual login process. """
    if request.method == 'POST':
        print('------- Post on Login ---------')
        pprint(request.form)
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
    return render_template('signup.html', signup_roles=[])


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You are now logged out.")
    return redirect(url_for('home'))


@app.route('/error', methods=['GET', 'POST'])
def error():
    err = request.form.get('data')
    return render_template('error.html', err=err)


@app.route('/admin')
@staff_required()
def admin(data=None):
    """ Platform Admin view to view links and actions unique to admin """
    dev_email = ['hepcatchris@gmail.com', 'christopherlchapman42@gmail.com']
    dev = current_user.email in dev_email
    # files = None if app.config.get('LOCAL_ENV') else all_files()
    files = None
    data = None
    return render_template('admin.html', dev=dev, data=data, files=files)


@app.route('/data/load/')
@login_required
def load_user():
    """ This is a temporary development function. Will be removed for production. """
    developer_admin.load()
    return redirect(url_for('all', mod='influencer'))


@app.route('/data/<string:mod>/<int:id>')
@login_required
def backup_save(mod, id):
    """ This is a temporary development function. Will be removed for production. """
    Model = mod_lookup(mod)
    count = developer_admin.save(mod, id, Model)
    message = f"We just backed up {count} {mod} model(s)"
    app.logger.info(message)
    flash(message)
    return redirect(url_for('view', mod='influencer', id=id))


# ########## The following are for worksheets ############


@app.route('/<string:mod>/<int:id>/export', methods=['GET', 'POST'])
def export(mod, id):
    """ Export data to google sheet, generally for influencer or brand Users.
        Was view results on GET and generate Sheet on POST .
    """
    app.logger.info(f"==== {mod} Create Sheet ====")
    Model = mod_lookup(mod)
    model = Model.query.get(id)  # db_read(id, Model=Model)
    sheet = create_sheet(model)
    # TODO: ?refactor to use redirect(url_for('data', mod=mod, id=id, sheet_id=sheet['id']))
    return render_template('data.html', mod=mod, id=id, sheet=sheet)

    # mod, view = 'campaign', 'results'
    # template, related = f"{view}_{mod}.html", {}
    # if request.method == 'POST':
    #     sheet = create_sheet(model)
    #     app.logger.info(f"==== {mod} Create Sheet ====")
    #     # TODO: ?refactor to use redirect(url_for('data', mod=mod, id=id, sheet_id=sheet['id']))
    #     return render_template('data.html', mod=mod, id=id, sheet=sheet)
    # app.logger.info(f'=========== {mod} Sheet Export ===========')
    # related = model.get_results()
    # return render_template(template, mod=mod, view=view, data=model, related=related)


@app.route('/data/update/<string:mod>/<int:id>/<string:sheet_id>')
def update_data(mod, id, sheet_id):
    """ Update the given worksheet (sheet_id) data from the given Model indicated by mod and id. """
    Model = mod_lookup(mod)
    model = Model.query.get(id)
    sheet = update_sheet(model, id=sheet_id)
    # TODO: ?refactor to use redirect(url_for('data', mod=mod, id=id, sheet_id=sheet['id']))
    return render_template('data.html', mod=mod, id=id, sheet=sheet)


@app.route('/data/permissions/<string:mod>/<int:id>/<string:sheet_id>', methods=['GET', 'POST'])
def data_permissions(mod, id, sheet_id, perm_id=None):
    """ Used for managing permissions for who has access to a worksheet """
    app.logger.info(f'===== {mod} data permissions for sheet {sheet_id} ====')
    template = 'form_permission.html'
    sheet = perm_list(sheet_id)
    data = next((x for x in sheet.get('permissions', []) if x.id == perm_id), {}) if perm_id else {}
    action = 'Edit' if perm_id else 'Add'
    app.logger.info(f'-------- {mod} Sheet {action} Permissions --------')
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        if action == 'Edit':
            # TODO: Manage updating the sheet permissions
            # model = db_update(data, id, Model=Model)
            pass
        else:  # action == 'Add'
            sheet = perm_add(sheet_id, data)
        # TODO: ?refactor to use redirect(url_for('data', mod=mod, id=id, sheet_id=sheet['id']))
        return render_template('data.html', mod=mod, id=id, sheet=sheet)
    return render_template(template, mod=mod, id=id, action=action, data=data, sheet=sheet)


@app.route('/data')
def data_default():
    # TODO: Do we need this route? Currently not called?
    return data(None)


@app.route('/data/view/<string:mod>/<int:id>/<string:sheet_id>')
def data(mod, id, sheet_id):
    """ Show the data with Google Sheets """
    # TODO: Do we need this route? Currently only called by unused routes
    # TODO: ?refactor to use redirect(url_for('data', mod=mod, id=id, sheet_id=sheet['id']))
    sheet = read_sheet(id=sheet_id)
    return render_template('data.html', mod=mod, id=id, sheet=sheet)
    # Influencer user should be redirected to their detail view page
    # Brand user should do what?
    # Otherwise Admin|Manager see a list.


# ############# End Worksheets #############


@app.route('/login/<string:mod>')
def fb_login(mod):
    """ Initiate the creation of a new Influencer or Brand, as indicated by 'mod' """
    app.logger.info(f'====================== NEW {mod} Account =========================')
    if app.config.get('LOCAL_ENV') is True:
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
        return render_template('decide_ig.html', mod=mod, id=account_id, ig_list=data)
    elif view == 'complete':
        return redirect(url_for('view', mod=mod, id=account_id))
    elif view == 'error':
        return redirect(url_for('error', data=data), code=307)
    else:
        return redirect(url_for('error', data='unknown response'), code=307)


@app.route('/campaign/<int:id>/results', methods=['GET', 'POST'])
def results(id):
    """ Campaign Results View (on GET) or generate Worksheet report (on POST) """
    mod, view = 'campaign', 'results'
    template, related = f"{view}_{mod}.html", {}
    campaign = Campaign.query.get(id)
    if request.method == 'POST':
        sheet = create_sheet(campaign)
        app.logger.info(f"==== Campaign {view} Create Sheet ====")
        # TODO: ?refactor to use redirect(url_for('data', mod=mod, id=id, sheet_id=sheet['id']))
        return render_template('data.html', mod=mod, id=id, sheet=sheet)
    app.logger.info(f'=========== Campaign {view} ===========')
    related = campaign.get_results()
    return render_template(template, mod=mod, view=view, data=campaign, related=related)


@app.route('/campaign/<int:id>/detail', methods=['GET', 'POST'])
def detail_campaign(id):
    """ Used because campaign function over-rides route for detail view """
    return campaign(id, view='collected')


@app.route('/campaign/<int:id>', methods=['GET', 'POST'])
def campaign(id, view='management'):
    """ Defaults to management of assigning posts to a campaign.
        When view is 'collected', user can review and re-assess posts already assigned to the campaign.
        On POST, updates the assigned media posts as indicated by the submitted form.
     """
    mod = 'campaign'
    template, related = f"{mod}.html", {}
    campaign = Campaign.query.get(id)
    app.logger.info(f'=========== Campaign {view} ===========')
    if request.method == 'POST':
        update_campaign(view, request)
    for user in campaign.users:
        if view == 'collected':
            related[user] = [post_display(ea) for ea in user.posts if ea.campaign_id == id]
        elif view == 'management':
            related[user] = [ea for ea in user.posts if not ea.processed]
        else:
            related[user] = []
    return render_template(template, mod=mod, view=view, data=campaign, related=related)


@app.route('/<string:mod>/<int:id>')
@login_required
def view(mod, id):
    """ Used primarily for specific User or Brand views, but also any data model view except Campaign. """
    Model, model = None, None
    if current_user.role not in ['manager', 'admin']:
        if mod in User.roles:
            if current_user.id != id or current_user.role != mod:
                flash('Incorrect location. You are being redirected to your own profile page')
                return redirect(url_for('view', mod=current_user.role, id=current_user.id))
            # otherwise they get to see their own profile page!
        elif mod in ['post', 'audience']:
            # The user can only view this detail view if they are associated to the data
            Model = mod_lookup(mod)
            model = db_read(id, Model=Model)
            if model.user != current_user:
                # ? Add the ability for brand user to see posts associated through a campaign?
                flash('Incorrect location. You are being redirected to the home page.')
                return redirect(url_for('home'))
        else:
            flash('This was not a correct location. You are redirected to the home page.')
            return redirect(url_for('home'))
    # Otherwise user is admin, manager, or a user looking at their own data.
    # if mod == 'campaign':
    #     return campaign(id)
    Model = Model or mod_lookup(mod)
    model = model or db_read(id, Model=Model)
    # model = Model.query.get(id)
    template = 'view.html'
    if mod == 'post':
        template = f"{mod}_{template}"
        model = post_display(model)
    elif mod == 'audience':
        template = f"{mod}_{template}"
        model['user'] = db_read(model.get('user_id')).get('name')
        value = json.loads(model['value'])
        if not isinstance(value, dict):  # For the id_data Audience records
            value = {'value': value}
        model['value'] = value
    elif mod == 'insight':
        template = f"{mod}_{template}"
        model['user'] = db_read(model.get('user_id')).get('name')
    return render_template(template, mod=mod, data=model)


@app.route('/<string:mod>/<int:id>/insights')
def insights(mod, id):
    """ For a given User (influencer or brand), show the account Insight data. """
    user = db_read(id)
    scheme_color = ['gold', 'purple', 'green', 'blue']
    dataset, i = {}, 0
    max_val, min_val = 4, float('inf')
    for metrics in (Insight.influence_metrics, Insight.profile_metrics, OnlineFollowers.metrics):
        for metric in metrics:
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
def new_audience(mod, id):
    """ Get new audience data from API for either. Input mod for either User or Brand, with given id. """
    audience = get_audience(id)
    logstring = f'Audience data for {mod} - {id}' if audience else f'No insight data, {mod}'
    app.logger.info(logstring)
    return redirect(url_for('view', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/followers')
def followers(mod, id):
    """ Get 'online_followers' report """
    follow_report = get_online_followers(id)
    logstring = f"Online Followers for {mod} - {id}" if follow_report else f"No data for {mod} - {id}"
    app.logger.info(logstring)
    return redirect(url_for('view', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/fetch')
def new_insight(mod, id):
    """ Get new account insight data from API. Input mod for either User or Brand, with given id. """
    insights = get_insight(id)
    logstring = f'Insight data for {mod} - {id} ' if insights else f'No insight data, {mod}'
    app.logger.info(logstring)
    return redirect(url_for('insights', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/posts')
def new_post(mod, id):
    """ Get new posts data from API. Input mod for either User or Brand, with a given id"""
    posts = get_posts(id)
    logstring = 'we got some posts back' if len(posts) else 'No posts retrieved'
    app.logger.info(logstring)
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
    app.logger.info(f'--------- {action} {mod}------------')
    if request.method == 'POST':
        data = process_form(mod, request)
        # TODO: ?Check for failing unique column fields, or failing composite unique requirements?
        if action == 'Edit':
            if Model == User and data.get('password'):
                # if form password field was blank, process_form removed the key from data
                data['password'] = generate_password_hash(data.get('password'))
            try:
                model = db_update(data, id, Model=Model)
            except ValueError as e:
                app.logger.error(e)
                flash('Please try again or contact an Admin')
                return redirect(url_for('edit', mod=mod, id=id))
        else:  # action == 'Add'
            try:
                model = db_create(data, Model=Model)
            except ValueError as e:
                app.logger.error(e)
                flash('Error. Please try again or contact an Admin')
                return redirect(url_for('add', mod=mod, id=id))
        return redirect(url_for('view', mod=mod, id=model['id']))
    template, related = 'form.html', {}
    model = db_read(id, Model=Model) if action == 'Edit' else {}
    if mod == 'campaign':
        template = f"{mod}_{template}"
        # add context for Brands and Users, only keeping id and name.
        users = User.query.filter_by(role='influencer').all()
        brands = User.query.filter_by(role='brand').all()
        related['users'] = [(ea.id, ea.name) for ea in users]
        related['brands'] = [(ea.id, ea.name) for ea in brands]
    return render_template(template, action=action, mod=mod, data=model, related=related)


@app.route('/<string:mod>/add', methods=['GET', 'POST'])
def add(mod):
    """ For a given data Model, as indicated by mod, add new data to DB. """
    valid_mod = {'campaign', 'brand'}
    if mod not in valid_mod:
        app.logger.error(f"Unable to add {mod}")
        flash(f"Adding a {mod} is not working right now. Contact an Admin")
        return redirect(request.referrer)
    return add_edit(mod, id=None)


@app.route('/<string:mod>/<int:id>/edit', methods=['GET', 'POST'])
def edit(mod, id):
    """ Modify the existing DB entry. Model indicated by mod, and provided record id. """
    valid_mod = {'campaign'}.union(set(User.roles))
    if mod not in valid_mod:
        app.logger.error(f"Unable to edit {mod}")
        flash(f"Editing a {mod} is not working right now. Contact an Admin")
        return redirect(request.referrer)
    return add_edit(mod, id=id)


@app.route('/<string:mod>/<int:id>/delete')
def delete(mod, id):
    """ Permanently remove from DB the record for Model indicated by mod and id. """
    Model = mod_lookup(mod)
    db_delete(id, Model=Model)
    return redirect(url_for('home'))


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
    # The following only runs if the user is an 'admin' or a 'manager' role.
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
    if page_name == 'favicon.ico':
        # TODO: Create favicon.ico for site
        return abort(404)
    return render_template('%s.html' % page_name)
