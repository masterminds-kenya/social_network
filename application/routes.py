from flask import current_app as app
from flask import render_template, redirect, url_for, request, abort, flash
from .model_db import db_create, db_read, db_update, db_delete, db_all
from .model_db import Brand, User, Insight, Audience, Post, Campaign  # , metric_clean
from . import developer_admin
from .manage import update_campaign, process_form, post_display
from .api import onboard_login, onboarding, get_insight, get_audience, get_posts
from .sheets import create_sheet, update_sheet, read_sheet, perm_add, perm_list
import json
# from pprint import pprint

mod_lookup = {'brand': User, 'user': User, 'insight': Insight, 'audience': Audience, 'post': Post, 'campaign': Campaign}


@app.route('/')
def home():
    """ Default root route """
    data = ''
    return render_template('index.html', data=data)


@app.route('/error', methods=['GET', 'POST'])
def error():
    err = request.form.get('data')
    return render_template('error.html', err=err)


@app.route('/dev_admin')
def dev_admin():
    """ Developer Admin view to help while developing the Application """
    return render_template('admin.html', data=None)


@app.route('/data/load/')
def load_user():
    """ This is a temporary development function. Will be removed for production. """
    developer_admin.load()
    return redirect(url_for('all', mod='user'))


@app.route('/data/<string:mod>/<int:id>')
def backup_save(mod, id):
    """ This is a temporary development function. Will be removed for production. """
    Model = mod_lookup.get(mod, None)
    if not Model:
        return f"No such route: {mod}", 404
    count = developer_admin.save(mod, id, Model)
    message = f"We just backed up {count} {mod} model(s)"
    app.logger.info(message)
    flash(message)
    return redirect(url_for('view', mod='user', id=id))


@app.route('/data/update/<int:campaign_id>/<string:sheet_id>')
def update_data(campaign_id, sheet_id):
    """ Update the worksheet data """
    campaign = Campaign.query.get(campaign_id)
    sheet = update_sheet(campaign, id=sheet_id)
    # TODO: ?refactor to use redirect(url_for('data', campaign_id=campaign_id, sheet_id=sheet['id']))
    return render_template('data.html', sheet=sheet, campaign_id=campaign_id)


@app.route('/data/permissions/<int:campaign_id>/<string:sheet_id>', methods=['GET', 'POST'])
def data_permissions(campaign_id, sheet_id, perm_id=None):
    """ Used for managing permissions to view worksheets """
    app.logger.info(f'===== data permissions route with sheet {sheet_id} ====')
    template = 'form_permission.html'
    sheet = perm_list(sheet_id)
    data = next((x for x in sheet.get('permissions', []) if x.id == perm_id), {}) if perm_id else {}
    action = 'Edit' if perm_id else 'Add'
    if request.method == 'POST':
        app.logger.info(f'--------- {action} Permissions ------------')
        data = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
        if action == 'Edit':
            # model = db_update(data, id, Model=Model)
            pass
        else:  # action == 'Add'
            sheet = perm_add(sheet_id, data)
        # TODO: ?refactor to use redirect(url_for('data', campaign_id=campaign_id, sheet_id=sheet['id']))
        return render_template('data.html', sheet=sheet, campaign_id=campaign_id)

    return render_template(template, action=action, data=data, sheet=sheet, campaign_id=campaign_id)


@app.route('/data')
def data_default():
    # TODO: Do we need this route? Currently not called?
    return data(None)


@app.route('/data/view/<string:id>')
def data(id):
    """ Show the data with Google Sheets """
    # TODO: Do we need this route? Currently only called by unused routes
    # TODO: ?refactor so url_for('data', campaign_id=campaign_id, sheet_id=sheet['id'])
    sheet = read_sheet(id=id)
    return render_template('data.html', sheet=sheet, campaign_id=None)


@app.route('/login/<string:mod>')
def login(mod):
    app.logger.info(f'====================== NEW {mod} Account =========================')
    authorization_url = onboard_login(mod)
    return redirect(authorization_url)


@app.route('/callback/<string:mod>')
def callback(mod):
    app.logger.info(f'================= Authorization Callback {mod}===================')
    view, data, account_id = onboarding(mod, request)
    # TODO: The following should be cleaned up with better error handling
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
    Model = mod_lookup.get(mod, None)
    campaign = Model.query.get(id)
    if request.method == 'POST':
        sheet = create_sheet(campaign)
        app.logger.info(f"==== Campaign {view} Create Sheet ====")
        # TODO: ?refactor to use redirect(url_for('data', campaign_id=campaign_id, sheet_id=sheet['id']))
        return render_template('data.html', sheet=sheet, campaign_id=id)
    app.logger.info(f'=========== Campaign {view} ===========')
    related = campaign.get_results()
    # print('--------related below------------')
    # pprint(related)
    return render_template(template, mod=mod, view=view, data=campaign, related=related)


@app.route('/campaign/<int:id>/detail', methods=['GET', 'POST'])
def detail_campaign(id):
    """ Used because campaign function over-rides route for detail view """
    return campaign(id, view='collected')


@app.route('/campaign/<int:id>', methods=['GET', 'POST'])
def campaign(id, view='management'):
    mod = 'campaign'
    template, related = f"{mod}.html", {}
    Model = mod_lookup.get(mod, None)
    model = Model.query.get(id)
    app.logger.info(f'=========== Campaign {view} ===========')
    if request.method == 'POST':
        update_campaign(view, request)
    for user in model.users:
        if view == 'collected':
            related[user] = [post_display(ea) for ea in user.posts if ea.campaign_id == id]
        elif view == 'management':
            related[user] = [ea for ea in user.posts if not ea.processed]
        else:
            related[user] = []
    return render_template(template, mod=mod, view=view, data=model, related=related)


@app.route('/<string:mod>/<int:id>')
def view(mod, id):
    """ Used primarily for specific User or Brand views, but also any data model view except Campaign. """
    # if mod == 'campaign':
    #     return campaign(id)
    Model = mod_lookup.get(mod, None)
    if not Model:
        return f"No such route: {mod}", 404
    model = db_read(id, Model=Model)
    # model = Model.query.get(id)
    template = 'view.html'
    if mod == 'post':
        template = f"{mod}_{template}"
        model = post_display(model)
    elif mod == 'audience':
        template = f"{mod}_{template}"
        model['user'] = db_read(model.get('user_id')).get('name')
        model['value'] = json.loads(model['value'])
    elif mod == 'insight':
        template = f"{mod}_{template}"
        model['user'] = db_read(model.get('user_id')).get('name')
    return render_template(template, mod=mod, data=model)


@app.route('/<string:mod>/<int:id>/insights')
def insights(mod, id):
    """ For a given User, show the account Insight data. """
    # TODO: update to also work for Brand
    user = db_read(id)
    Model = Insight
    scheme_color = ['gold', 'purple', 'green']
    dataset = {}
    i = 0
    max_val, min_val = 4, 0
    for metric in Model.metrics:
        query = Model.query.filter_by(user_id=id, name=metric).order_by('recorded').all()
        temp_data = {ea.recorded.strftime("%d %b, %Y"): int(ea.value) for ea in query}
        max_curr = max(*temp_data.values())
        min_curr = min(*temp_data.values())
        max_val = max(max_val, max_curr)
        min_val = min(max_val, min_curr)
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
    steps = 14
    return render_template('chart.html', user=user['name'], dataset=dataset, labels=labels, max=max_val, min=min_val, steps=steps)


@app.route('/<string:mod>/<int:id>/audience')
def new_audience(mod, id):
    """ Get new audience data from API. Input mod for either User or Brand, with given id. """
    # TODO: update to also work for Brand
    audience = get_audience(id)
    logstring = f'Audience data for {mod} - {id}' if audience else f'No insight data, {mod}'
    app.logger.info(logstring)
    return redirect(url_for('view', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/fetch')
def new_insight(mod, id):
    """ Get new account insight data from API. Input mod for either User or Brand, with given id. """
    # TODO: update to also work for Brand
    insights = get_insight(id)
    logstring = f'Insight data for {mod} - {id} ' if insights else f'No insight data, {mod}'
    app.logger.info(logstring)
    return redirect(url_for('insights', mod=mod, id=id))


@app.route('/<string:mod>/<int:id>/posts')
def new_post(mod, id):
    """ Get new posts data from API. Input mod for either User or Brand, with a given id"""
    # TODO: ?update to also work for Brand?
    posts = get_posts(id)
    logstring = 'we got some posts back' if len(posts) else 'No posts retrieved'
    app.logger.info(logstring)
    return_path = request.referrer
    return redirect(return_path)
    # return redirect(url_for('view', mod=mod, id=id))


def add_edit(mod, id=None):
    """ Adding or Editing a DB record is a similar process handled here. """
    action = 'Edit' if id else 'Add'
    Model = mod_lookup.get(mod, None)
    if not Model:
        return f"No such route: {mod}", 404
    if request.method == 'POST':
        app.logger.info(f'--------- {action} {mod}------------')
        data = process_form(mod, request)
        # TODO: ?Check for failing unique column fields, or failing composite unique requirements?
        if action == 'Edit':
            model = db_update(data, id, Model=Model)
        else:  # action == 'Add'
            model = db_create(data, Model=Model)
        return redirect(url_for('view', mod=mod, id=model['id']))
    template, related = 'form.html', {}
    model = db_read(id, Model=Model) if action == 'Edit' else {}
    if mod == 'campaign':
        template = f"{mod}_{template}"
        # add context for Brands and Users, only keeping id and name.
        users = User.query.all()
        brands = Brand.query.all()
        related['users'] = [(ea.id, ea.name) for ea in users]
        related['brands'] = [(ea.id, ea.name) for ea in brands]
    return render_template(template, action=action, mod=mod, data=model, related=related)


@app.route('/<string:mod>/add', methods=['GET', 'POST'])
def add(mod):
    """ For a given data Model, as indicated by mod, add new data to DB. """
    return add_edit(mod, id=None)


@app.route('/<string:mod>/<int:id>/edit', methods=['GET', 'POST'])
def edit(mod, id):
    """ Modify the existing DB entry. Model indicated by mod, and provided record id. """
    return add_edit(mod, id=id)


@app.route('/<string:mod>/<int:id>/delete')
def delete(mod, id):
    """ Permanently remove from DB the record for Model indicated by mod and id. """
    Model = mod_lookup.get(mod, None)
    if not Model:
        return f"No such route: {mod}", 404
    db_delete(id, Model=Model)
    return redirect(url_for('home'))


@app.route('/<string:mod>/list')
def all(mod):
    """ List view for all data of Model indicated by mod. """
    Model = mod_lookup.get(mod, None)
    if not Model:
        return f"No such route: {mod}", 404
    models = db_all(Model=Model)
    return render_template('list.html', mod=mod, data=models)


# Catchall redirect route.
@app.route('/<string:page_name>/')
def render_static(page_name):
    """ Catch all for undefined routes. Return the requested static page. """
    if page_name == 'favicon.ico':
        return abort(404)
    return render_template('%s.html' % page_name)
