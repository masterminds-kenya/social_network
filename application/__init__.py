# import logging
from flask import Flask, render_template, abort, request, redirect, url_for  # , current_app
from . import model_db
from . import sheet_setup
import requests
import requests_oauthlib
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
import json
from os import environ
from datetime import datetime as dt
from datetime import timedelta

USER_FILE = 'env/user_save.txt'
FB_CLIENT_ID = environ.get('FB_CLIENT_ID')
FB_CLIENT_SECRET = environ.get('FB_CLIENT_SECRET')
FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
SHARED_SHEET_ID = '1LyUFeo5in3F-IbR1eMnkp-XeQXD_zvfYraxCJBUkZPs'
FB_SCOPE = [
    'pages_show_list',
    'instagram_basic',
    'instagram_manage_insights',
        ]
mod_lookup = {'brand': model_db.Brand, 'user': model_db.User, 'insight': model_db.Insight, 'audience': model_db.Audience, 'post': model_db.Post, 'campaign': model_db.Campaign}
DEPLOYED_URL = environ.get('DEPLOYED_URL')
LOCAL_URL = 'http://127.0.0.1:8080'
if environ.get('GAE_INSTANCE'):
    URL = DEPLOYED_URL
    LOCAL_ENV = False
else:
    environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    URL = LOCAL_URL
    LOCAL_ENV = True


def process_form(mod, request):
    # If Model has relationship collections set in form, then we must capture these before flattening the input
    # I believe this is only needed for campaigns.
    save = {}
    if mod == 'campaign':
        data = request.form.to_dict(flat=False)  # TODO: add form validate method for security.
        # capture the relationship collections
        rel_collections = (('brands', model_db.Brand), ('users', model_db.User), ('posts', model_db.Post))
        for rel, Model in rel_collections:
            if rel in data:
                model_ids = [int(ea) for ea in data[rel]]
                models = Model.query.filter(Model.id.in_(model_ids)).all()
                save[rel] = models
    data = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
    data.update(save)  # update if we did save some relationship collections
    # If the form has a checkbox for a Boolean in the form, we may need to reformat.
    # currently I think only Campaign and Post have checkboxes
    bool_fields = {'campaign': 'completed', 'post': 'processed'}
    if mod in bool_fields:
        data[bool_fields[mod]] = True if data.get(bool_fields[mod]) in {'on', True} else False
    return data


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
    return model_db.create_many(results, model_db.Insight)


def get_audience(user_id, ig_id=None, facebook=None):
    """ Get the audience data for the user of user_id """
    # print('=========================== Get Audience Data ======================')
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
    return model_db.create_many(results, model_db.Audience)


def get_posts(user_id, ig_id=None, facebook=None):
    """ Get media posts """
    from pprint import pprint
    print('==================== Get Posts ====================')
    post_metrics = {key: ','.join(val) for (key, val) in model_db.Post.metrics.items()}
    results, token = [], ''
    if not facebook or not ig_id:
        model = model_db.read(user_id, safe=False)
        ig_id, token = model.get('instagram_id'), model.get('token')
    print('================ Media Posts ====================')
    url = f"https://graph.facebook.com/{ig_id}/media"
    response = facebook.get(url).json() if facebook else requests.get(f"{url}?access_token={token}").json()
    media = response.get('data')
    if not isinstance(media, list):
        print('Error: ', response.get('error'))
        print('--------------- Instead, response was ----------------')
        pprint(response)
        return []
    print(f"----------- Looking up {len(media)} Media Posts ----------- ")
    for post in media:
        media_id = post.get('id')
        url = f"https://graph.facebook.com/{media_id}?fields={post_metrics['basic']}"
        res = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
        res['media_id'] = res.pop('id', media_id)
        res['user_id'] = user_id
        metrics = post_metrics.get(res.get('media_type'), post_metrics['insight'])
        if metrics == post_metrics['insight']:  # TODO: remove after tested
            print(f"----- Match not found for {res.get('media_type')} media_type parameter -----")  # TODO: remove after tested
        url = f"https://graph.facebook.com/{media_id}/insights?metric={metrics}"
        res_insight = facebook.get(url).json() if facebook else requests.get(f"{url}&access_token={token}").json()
        insights = res_insight.get('data')
        if insights:
            temp = {ea.get('name'): ea.get('values', [{'value': 0}])[0].get('value', 0) for ea in insights}
            res.update(temp)
        else:
            print(f"media {media_id} had NO INSIGHTS for type {res.get('media_type')} --- {res_insight}")
        pprint(res)
        print('---------------------------------------')
        results.append(res)
    return model_db.create_many(results, model_db.Post)


def get_ig_info(ig_id, token=None, facebook=None):
    """ We already have their InstaGram Business Account id, but we need their IG username """
    from pprint import pprint
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
    ig_id, ig_set = None, set()
    pages = [page.get('id') for page in accounts.get('data')] if accounts and 'data' in accounts else None
    # TODO: Update logic for user w/ many pages/instagram-accounts. Currently assumes last found instagram account
    if pages:
        print(f'================= Pages count: {len(pages)} =================================')
        for page in pages:
            instagram_data = facebook.get(f"https://graph.facebook.com/v4.0/{page}?fields=instagram_business_account").json()
            ig_business = instagram_data.get('instagram_business_account', None)
            if ig_business:
                ig_set.add(ig_business.get('id', None))
        ig_id = ig_set.pop()
    return (ig_id, ig_set)


def create_app(config, debug=False, testing=False, config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = debug
    app.testing = testing
    if config_overrides:
        app.config.update(config_overrides)
    # # Configure logging
    # if not app.testing:
    #     logging.basicConfig(level=logging.INFO)
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
        new_users = []
        with open(USER_FILE, 'r') as file:
            for line in file.readlines():
                user = json.loads(line)
                if 'email' in user:
                    del user['email']
                ig_id, token = user.get('instagram_id'), user.get('token')
                ig_info = get_ig_info(ig_id, token=token)
                user['username'] = ig_info.get('username')
                print(user['username'])
                new_users.append(user)
        created_users = model_db.create_many(new_users)
        print(f'------------- Create from File: {len(created_users)} users -------------')
        return redirect(url_for('all', mod='user'))

    @app.route('/data/<string:mod>/<int:id>')
    def migrate_save(mod, id):
        if mod == 'user':
            filename = USER_FILE
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        model = model_db.read(id, Model=Model, safe=False)
        del model['id']
        model.pop('created', None)
        model.pop('modified', None)
        model.pop('insight', None)
        model.pop('audience', None)
        print('Old Account: ', model)
        with open(filename, 'a') as file:
            file.write(json.dumps(model))
            file.write('\n')
        return redirect(url_for('view', mod='user', id=id))

    @app.route('/data/update/<string:id>')
    def update_data(id):
        """ Update the worksheet data """
        spreadsheet, id = sheet_setup.update_sheet(LOCAL_ENV, id)
        return redirect(url_for('data', id=id))

    @app.route('/data/create')
    def create_data():
        """ Create a worksheet to hold report data """
        spreadsheet, id = sheet_setup.create_sheet(LOCAL_ENV, 'test-title')
        return redirect(url_for('data', id=id))

    @app.route('/data')
    def data_default():
        id = SHARED_SHEET_ID
        return redirect(url_for('data', id=id))

    @app.route('/data/view/<string:id>')
    def data(id):
        """ Show the data with Google Sheets """
        spreadsheet, id = sheet_setup.read_sheet(LOCAL_ENV, id)
        link = '' if id == 0 else f"https://docs.google.com/spreadsheets/d/{id}/edit#gid=0"
        return render_template('data.html', data=spreadsheet, id=id, link=link)

    @app.route('/login')
    def login():
        print('============================= NEW LOGIN ================================')
        callback = URL + '/callback'
        facebook = requests_oauthlib.OAuth2Session(
            FB_CLIENT_ID, redirect_uri=callback, scope=FB_SCOPE
        )
        authorization_url, state = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)
        # session['oauth_state'] = state
        return redirect(authorization_url)

    @app.route('/callback')
    def callback():
        from pprint import pprint
        print('========================== Authorization Callback =============================')
        callback = URL + '/callback'
        facebook = requests_oauthlib.OAuth2Session(FB_CLIENT_ID, scope=FB_SCOPE, redirect_uri=callback)
        facebook = facebook_compliance_fix(facebook)  # we need to apply a fix for Facebook here
        token = facebook.fetch_token(FB_TOKEN_URL, client_secret=FB_CLIENT_SECRET, authorization_response=request.url)
        if 'error' in token:
            return redirect(url_for('error'), data=token, code=307)
        # Fetch a protected resources:
        facebook_user_data = facebook.get("https://graph.facebook.com/me?fields=id,accounts").json()
        if 'error' in facebook_user_data:
            return redirect(url_for('error'), data=facebook_user_data, code=307)
        # TODO: use a better constructor for the user account.
        data = facebook_user_data.copy()  # .to_dict(flat=True)
        data['token'] = token
        accounts = data.pop('accounts')
        ig_id, ig_set = find_instagram_id(accounts, facebook=facebook)
        ig_info = get_ig_info(ig_id, token=None, facebook=facebook)
        data['name'] = ig_info.get('username', 'NA')
        data['instagram_id'], data['notes'] = ig_id, json.dumps(list(ig_set))  # json.dumps(media)
        print('=================== Data sent to Create User =======================')
        pprint(data)
        user = model_db.create(data)
        user_id = user.get('id')
        print('User: ', user_id)
        # Relate Data
        insights = get_insight(user_id, last=90, ig_id=ig_id, facebook=facebook)
        print('We have insights') if insights else print('No insights')
        audience = get_audience(user_id, ig_id=ig_id, facebook=facebook)
        print('Audience data collected') if audience else print('No Audience data')
        return redirect(url_for('view', mod='user', id=user_id))

    @app.route('/campaign/<int:id>', methods=['GET', 'POST'])
    def campaign(id):
        mod, template = 'campaign', 'campaign.html'
        Model = mod_lookup.get(mod, None)
        model = Model.query.get(id)
        if request.method == 'POST':
            print('=========== Updating Campaign Posts ===========')
            form_dict = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
            # print(request.form)
            # temp = {key: int(val) for key, val in ea for ea in request.form}
            # temp = {ea[0].replace('assign_', ''): int(ea[1]) for ea in request.form}
            # print(temp)
            data = {int(key.replace('assign_', '')): int(val) for (key, val) in form_dict.items() if val != '0'}
            related = model_db.Post.query.filter(model_db.Post.id.in_(data.keys())).all()
            for post in related:
                post.processed = True
                post.campaign_id = data[post.id] if data[post.id] > 0 else None
            model_db.db.session.commit()

        # model = model_db.read(id, Model=Model)
        return render_template(template, mod=mod, data=model)

    @app.route('/<string:mod>/<int:id>')
    def view(mod, id):
        """ Used primarily for specific User or Brand views, but also any data model view. """
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        model = model_db.read(id, Model=Model)
        template = 'view.html'
        if mod == 'post':
            template = f"{mod}_{template}"
            fields = {'id', 'user_id', 'campaign_id', 'processed', 'recorded'}
            fields.update(Model.metrics['basic'])
            fields.discard('timestamp')
            fields.update(Model.metrics[model['media_type']])
            model = {key: val for (key, val) in model.items() if key in fields}
            # model = {key: model[key] for key in fields}
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
        """ For a given User, show all Insight data. """
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
        return redirect(url_for('view', mod=mod, id=id))

    @app.route('/<string:mod>/<int:id>/fetch')
    def new_insight(mod, id):
        """ Get new insight data from API. Input mod for either User or Brand, with given id. """
        # print('=========================== Get Insight Data ======================')
        insights = get_insight(id)
        print(f'Insight data for {mod} - {id} ') if insights else (f'No insight data, {mod} - {data}')
        return redirect(url_for('insights', mod=mod, id=id))

    @app.route('/<string:mod>/<int:id>/posts')
    def new_post(mod, id):
        """ Get new posts data from API. Input mod for either User or Brand, with a given id"""
        posts = get_posts(id)
        if len(posts):
            print('we got some posts back')

        return redirect(url_for('view', mod=mod, id=id))

    @app.route('/<string:mod>/add', methods=['GET', 'POST'])
    def add(mod):
        """ For a given data Model, as indicated by mod, add new data to DB. """
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        if request.method == 'POST':
            print('--------- add ------------')
            data = process_form(mod, request)
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
            print('--------- edit ------------')
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

    # Add an error handler. This is useful for debugging the live application,
    # however, you should disable the output of the exception for production
    # applications.
    @app.errorhandler(500)
    def server_error(e):
        print('================== Error Handler =====================')
        print(e)
        print('================== End Error Handler =================')
        return """
        An internal error occurred: <pre>{}</pre>
        See logs for full stacktrace.
        """.format(e), 500

    return app
