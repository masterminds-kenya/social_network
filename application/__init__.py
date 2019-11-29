import logging
from flask import Flask, render_template, abort, request, flash, redirect, url_for  # , current_app
from . import model_db
from . import developer_admin
from .manage import update_campaign, process_form, post_display
from .api import onboard_login, onboarding, get_insight, get_audience, get_posts
from .sheets import create_sheet, update_sheet, read_sheet
import json
from os import environ

DEPLOYED_URL = environ.get('DEPLOYED_URL')
LOCAL_URL = 'http://127.0.0.1:8080'
# URL, LOCAL_ENV = '', ''
if environ.get('GAE_INSTANCE'):
    URL = DEPLOYED_URL
    LOCAL_ENV = False
else:
    environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    URL = LOCAL_URL
    LOCAL_ENV = True
mod_lookup = {'brand': model_db.Brand, 'user': model_db.User, 'insight': model_db.Insight, 'audience': model_db.Audience, 'post': model_db.Post, 'campaign': model_db.Campaign}


class Result:
    """ used for campaign results """

    def __init__(self, media_type=None, metrics=set()):
        self.media_type = media_type
        self.posts = []
        self.metrics = Result.lookup_metrics[self.media_type]

    @staticmethod
    def define_metrics():
        rejected = {'insight', 'basic'}
        added = {'comments_count', 'like_count'}
        metrics = {k: v.extend(added) for k, v in model_db.Post.metrics.items() if k not in rejected}
        return metrics

    lookup_metrics = define_metrics()


def create_app(config, debug=False, testing=False, config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = debug
    app.testing = testing
    if config_overrides:
        app.config.update(config_overrides)
    # Configure logging
    if not app.testing:
        logging.basicConfig(level=logging.INFO)
    # Setup the data model.
    with app.app_context():
        model = model_db
        model.init_app(app)

    # Routes
    @app.route('/')
    def home():
        """ Default root route """
        data = ''
        return render_template('index.html', data=data)

    @app.route('/error', methods=['GET', 'POST'])
    def error():
        err = request.form.get('data')
        return render_template('error.html', err=err)

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
        app.logger.info(f"We just backed up {count} model(s)")
        return redirect(url_for('view', mod='user', id=id))

    @app.route('/data/update/<string:id>')
    def update_data(id):
        """ Update the worksheet data """
        spreadsheet, id = update_sheet(LOCAL_ENV, id)
        return redirect(url_for('data', id=id))

    @app.route('/data/create')
    def create_data():
        """ Create a worksheet to hold report data """
        spreadsheet, id = create_sheet(LOCAL_ENV, 'test-title')
        return redirect(url_for('data', id=id))

    @app.route('/data')
    def data_default():
        return data(None)

    @app.route('/data/view/<string:id>')
    def data(id):
        """ Show the data with Google Sheets """
        spreadsheet, id = read_sheet(LOCAL_ENV, id)
        link = '' if id == 0 else f"https://docs.google.com/spreadsheets/d/{id}/edit#gid=0"
        return render_template('data.html', data=spreadsheet, id=id, link=link)

    @app.route('/login/<string:mod>')
    def login(mod):
        app.logger.info(f'====================== NEW {mod} Account =========================')
        authorization_url = onboard_login(URL, mod)
        return redirect(authorization_url)

    @app.route('/callback/<string:mod>')
    def callback(mod):
        app.logger.info(f'================= Authorization Callback {mod}===================')
        view, data, account_id = onboarding(URL, mod, request)
        # TODO: The following should be cleaned up with better error handling
        if view == 'decide':
            return render_template('decide_ig.html', mod=mod, id=account_id, ig_list=data)
        elif view == 'complete':
            return redirect(url_for('view', mod=mod, id=account_id))
        elif view == 'error':
            return redirect(url_for('error', data=data), code=307)
        else:
            return redirect(url_for('error', data='unknown response'), code=307)

    @app.route('/campaign/<int:id>/results')
    def results(id):
        mod, view = 'campaign', 'results'
        template, related = f"{mod}.html", {}
        Model = mod_lookup.get(mod, None)
        campaign = Model.query.get(id)
        app.logger.info(f'=========== Campaign {view} ===========')
        rejected = {'insight', 'basic'}
        added = {'comments_count', 'like_count'}
        lookup = {k: v.extend(added) for k, v in model_db.Post.metrics.items() if k not in rejected}
        related = {key: {'posts': [], 'metrics': lookup[key]} for key in lookup}
        for post in campaign.posts:
            media_type = post.media_type
            related[media_type]['posts'].append(post)
        return render_template(template, mod=mod, view=view, data=campaign, related=related)

    @app.route('/campaign/<int:id>/detail', methods=['GET', 'POST'])
    def detail_campaign(id):
        """ Used because campaign function over-rides route for detail view """
        return campaign(id, view='collected')

    @app.route('/campaign/<int:id>', methods=['GET', 'POST'])
    def campaign(id, view='management'):
        # mod, view = 'campaign', 'management'
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
        print('------------')
        print(model)
        return render_template(template, mod=mod, view=view, data=model, related=related)

    @app.route('/<string:mod>/<int:id>')
    def view(mod, id):
        """ Used primarily for specific User or Brand views, but also any data model view. """
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        model = model_db.read(id, Model=Model)
        # model = Model.query.get(id)
        template = 'view.html'
        if mod == 'post':
            template = f"{mod}_{template}"
            model = post_display(model)
        elif mod == 'audience':
            template = f"{mod}_{template}"
            model['user'] = model_db.read(model.get('user_id')).get('name')
            model['value'] = json.loads(model['value'])
        elif mod == 'insight':
            template = f"{mod}_{template}"
            model['user'] = model_db.read(model.get('user_id')).get('name')
        return render_template(template, mod=mod, data=model)

    @app.route('/<string:mod>/<int:id>/insights')
    def insights(mod, id):
        """ For a given User, show the account Insight data. """
        user = model_db.read(id)
        Model = model_db.Insight
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
        audience = get_audience(id)
        logstring = f'Audience data for {mod} - {id}' if audience else f'No insight data, {mod}'
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
        # return redirect(url_for('view', mod=mod, id=id))

    @app.route('/<string:mod>/add', methods=['GET', 'POST'])
    def add(mod):
        """ For a given data Model, as indicated by mod, add new data to DB. """
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        if request.method == 'POST':
            app.logger.info(f'--------- add {mod}------------')
            data = process_form(mod, request)
            # TODO: ?Check for failing unique column fields, or failing composite unique requirements?
            model = model_db.create(data, Model=Model)
            return redirect(url_for('view', mod=mod, id=model['id']))
        # template = f"{mod}_form.html"
        template, related = 'form.html', {}
        if mod == 'campaign':
            template = f"{mod}_{template}"
            # TODO: Modify query to only get the id and name fields?
            users = model_db.User.query.all()
            brands = model_db.Brand.query.all()
            related['users'] = [(ea.id, ea.name) for ea in users]
            related['brands'] = [(ea.id, ea.name) for ea in brands]
        return render_template(template, action='Add', mod=mod, data={}, related=related)

    @app.route('/<string:mod>/<int:id>/edit', methods=['GET', 'POST'])
    def edit(mod, id):
        """ Modify the existing DB entry. Model indicated by mod, and provided DB id. """
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        if request.method == 'POST':
            app.logger.info(f'--------- edit {mod}------------')
            data = process_form(mod, request)
            model = model_db.update(data, id, Model=Model)
            return redirect(url_for('view', mod=mod, id=model['id']))
        model = model_db.read(id, Model=Model)
        # template = f"{mod}_form.html"
        template, related = 'form.html', {}
        if mod == 'campaign':
            template = f"{mod}_{template}"
            # add context for Brands and Users
            # list of all users & brands, only keep id and name.
            users = model_db.User.query.all()
            brands = model_db.Brand.query.all()
            related['users'] = [(ea.id, ea.name) for ea in users]
            related['brands'] = [(ea.id, ea.name) for ea in brands]
        return render_template(template, action='Edit', mod=mod, data=model, related=related)

    @app.route('/<string:mod>/<int:id>/delete')
    def delete(mod, id):
        """ Permanently remove from DB the record for Model indicated by mod and id. """
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        model_db.delete(id, Model=Model)
        return redirect(url_for('home'))

    @app.route('/<string:mod>/list')
    def all(mod):
        """ List view for all data of Model indicated by mod. """
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        models = model_db.all(Model=Model)
        return render_template('list.html', mod=mod, data=models)

    # Catchall redirect route.
    @app.route('/<string:page_name>/')
    def render_static(page_name):
        """ Catch all for undefined routes. Return the requested static page. """
        if page_name == 'favicon.ico':
            return abort(404)
        return render_template('%s.html' % page_name)

    # TODO: For production, the output of the error should be disabled.
    @app.errorhandler(500)
    def server_error(e):
        app.logger.error('================== Error Handler =====================')
        app.logger.error(e)
        return """
        An internal error occurred: <pre>{}</pre>
        See logs for full stacktrace.
        """.format(e), 500

    return app
