# import logging
from flask import Flask, render_template, abort, request, redirect, url_for  # , current_app
from . import model_db
import requests
import requests_oauthlib
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
import json
from os import environ
from datetime import datetime as dt
from datetime import timedelta

FB_CLIENT_ID = environ.get('FB_CLIENT_ID')
FB_CLIENT_SECRET = environ.get('FB_CLIENT_SECRET')
FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
FB_SCOPE = [
    'email',
    'pages_show_list',
    'instagram_basic',
    'instagram_manage_insights',
        ]
mod_lookup = {'brand': model_db.Brand, 'user': model_db.User, 'insight': model_db.Insight, 'audience': model_db.Audience}
DEPLOYED_URL = environ.get('DEPLOYED_URL')
if environ.get('GAE_INSTANCE'):
    URL = DEPLOYED_URL
else:
    environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    URL = 'http://127.0.0.1:8080'


def get_insight(user_id, first=1, last=30*12, ig_id=None, facebook=None):
    """ Practice getting some insight data with the provided facebook oauth session """
    ig_period = 'day'
    results = []
    insight_metric = ','.join(model_db.Insight.metrics)
    # insight_metric = {'impressions', 'reach', 'follower_count'}
    if not facebook or not ig_id:
        model = model_db.read(user_id, safe=False)
        ig_id, token = model.get('instagram_id'), model.get('token')

    for i in range(first, last + 2 - 30, 30):
        until = dt.utcnow() - timedelta(days=i)
        since = until - timedelta(days=30)
        url = f"https://graph.facebook.com/{ig_id}/insights?metric={insight_metric}&period={ig_period}&since={since}&until={until}"
        auth_url = f"{url}&access_token={token}"
        response = requests.get(auth_url).json() if not facebook else facebook(url).json()
        print('============ Test Insights Data ====================')
        test_insights = response.get('data')
        if not test_insights:
            print('Error: ', response.get('error'))
            return None
        for ea in test_insights:
            for val in ea.get('values'):
                val['name'], val['user_id'] = ea.get('name'), user_id
                temp = model_db.create(val, model_db.Insight)
                print(temp.get('id'))
                results.append(temp)
    return results


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

    @app.route('/login')
    def login():
        callback = URL + '/callback'
        facebook = requests_oauthlib.OAuth2Session(
            FB_CLIENT_ID, redirect_uri=callback, scope=FB_SCOPE
        )
        authorization_url, state = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)
        # session['oauth_state'] = state
        return redirect(authorization_url)

    @app.route('/callback')
    def callback():
        callback = URL + '/callback'
        facebook = requests_oauthlib.OAuth2Session(FB_CLIENT_ID, scope=FB_SCOPE, redirect_uri=callback)
        # we need to apply a fix for Facebook here
        facebook = facebook_compliance_fix(facebook)
        token = facebook.fetch_token(FB_TOKEN_URL, client_secret=FB_CLIENT_SECRET, authorization_response=request.url)
        if 'error' in token:
            return redirect(url_for('error'), data=token, code=307)
        # Fetch a protected resources:
        facebook_user_data = facebook.get("https://graph.facebook.com/me?fields=id,name,email,accounts").json()
        if 'error' in facebook_user_data:
            return redirect(url_for('error'), data=facebook_user_data, code=307)
        # TODO: use a better constructor for the user account.
        data = facebook_user_data.copy()  # .to_dict(flat=True)
        data['token'] = token  # TODO: Decide - Should we pass this differently to protect this key?
        accounts = data.pop('accounts')
        pages = [page.get('id') for page in accounts.get('data')] if accounts and 'data' in accounts else None
        # TODO: Add logic for user w/ many pages/instagram-accounts. Currently assume 1st page is correct one.
        if pages:
            instagram_data = facebook.get(f"https://graph.facebook.com/v4.0/{pages[0]}?fields=instagram_business_account").json()
            ig_id = instagram_data['instagram_business_account'].get('id')
            audience_metric = {'audience_city', 'audience_country', 'audience_gender_age'}
            ig_period = 'lifetime'
            url = f"https://graph.facebook.com/{ig_id}/insights?metric={','.join(audience_metric)}&period={ig_period}"
            audience = facebook.get(url).json()
            # url = f"https://graph.facebook.com/v4.0/{ig_id}/media"
            # media = facebook.get(url).json()
            # if audience.get('error') or insights.get('error') or media.get('error'):
            #     print('----------- Error! ----------------')
            #     print(audience, insights, media)
            #     return redirect(url_for('error'), data=[audience, insights, media], code=307)
            data['instagram_id'], data['notes'] = ig_id, ''  # json.dumps(media)
        else:
            data['instagram_id'], data['notes'] = None, ''
        user = model_db.create(data)
        user_id = user.get('id')
        print('User: ', user_id)
        # insight_metric = {'impressions', 'reach', 'follower_count'}
        insight_metric = ','.join(model_db.Insight.metrics)
        ig_period = 'day'
        for i in range(1, 360 + 2 - 30, 30):
            until = dt.utcnow() - timedelta(days=i)
            since = until - timedelta(days=30)
            url = f"https://graph.facebook.com/{ig_id}/insights?metric={insight_metric}&period={ig_period}&since={since}&until={until}"
            response = facebook.get(url).json()
            test_insights = response.get('data')
            if not test_insights:
                print('Error: ', response.get('error'))
                return None
            for ea in test_insights:
                for val in ea.get('values'):
                    val['name'], val['user_id'] = ea.get('name'), user_id
                    temp = model_db.create(val, model_db.Insight)
                    print('Insight: ', temp.get('id'))
        for ea in audience.get('data'):
            ea['user_id'] = user_id
            temp = model_db.create(ea, model_db.Audience)
            print('Audience: ', temp['id'], ea.get('name'))
            print(temp)
        return redirect(url_for('view', mod='user', id=user_id))

    @app.route('/<string:mod>/<int:id>')
    def view(mod, id):
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        model = model_db.read(id, Model=Model)
        if mod == 'audience':
            # prep some data
            model['user'] = model_db.read(model.get('user_id')).get('name')
            model['value'] = json.loads(model['value'])
            return render_template(f"{mod}_view.html", mod=mod, data=model)
        elif mod == 'insight':
            # prep some data
            model['user'] = model_db.read(model.get('user_id')).get('name')
            return render_template(f"{mod}_view.html", mod=mod, data=model)
        return render_template('view.html', mod=mod, data=model)

    @app.route('/<string:mod>/<int:id>/insights')
    def insights(mod, id):
        Model = model_db.Insight
        dataset, dates = {}, {}
        scheme_color = ['gold', 'purple', 'green']
        i = 0
        for metric in Model.metrics:
            temp = {}
            temp['color'] = scheme_color[i % len(scheme_color)]
            query = Model.query.filter_by(user_id=id, name=metric).order_by('recorded').all()
            temp['data'] = {ea.recorded: int(ea.value) for ea in query}
            dataset[metric] = temp
            i += 1

        titles = dataset['reach']['data'].keys()
        nums1 = [int(ea) for ea in dataset['impressions']['data'].values()]
        nums2 = [int(ea) for ea in dataset['reach']['data'].values()]
        nums3 = [int(ea) for ea in dataset['follower_count']['data'].values()]
        colors = [dataset[metric]['color'] for metric in dataset]
        max_val = int(1.2 * max(max(nums1), max(nums2), max(nums3), 9))
        min_val = int(0.8 * min(min(nums1), min(nums2), min(nums3)))
        steps = 14
        # return render_template('insight_view.html', mod=mod, data=data)
        return render_template('chart.html', colors=colors, data=dataset, max=max_val, min=min_val, steps=steps, vals1=nums1, vals2=nums2, vals3=nums3, labels=titles)

    @app.route('/<string:mod>/<int:id>/fetch')
    def new_insight(mod, id):
        # mod is either 'brand' or 'user'
        new_insight = get_insight(id)
        return render_template('test.html', data=new_insight)

    @app.route('/<string:mod>/add', methods=['GET', 'POST'])
    def add(mod):
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        if request.method == 'POST':
            data = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
            model = model_db.create(data, Model=Model)
            return redirect(url_for('view', mod=mod, id=model['id']))
        template = f"{mod}_form.html"
        return render_template(template, action='Add', mod=mod, data={})

    @app.route('/<string:mod>/<int:id>/edit', methods=['GET', 'POST'])
    def edit(mod, id):
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        if request.method == 'POST':
            data = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
            model = model_db.update(data, id, Model=Model)
            return redirect(url_for('view', mod=mod, id=model['id']))
        model = model_db.read(id, Model=Model)
        template = f"{mod}_form.html"
        return render_template(template, action='Edit', mod=mod, data=model)

    @app.route('/<string:mod>/<int:id>/delete')
    def delete(mod, id):
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        model_db.delete(id, Model=Model)
        return redirect(url_for('home'))

    @app.route('/<string:mod>/list')
    def all(mod):
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
