# import logging
from flask import Flask, render_template, abort, request, redirect, url_for  # , current_app
from . import model_db
import requests_oauthlib
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
import json
from os import environ

FB_CLIENT_ID = environ.get("FB_CLIENT_ID")
FB_CLIENT_SECRET = environ.get("FB_CLIENT_SECRET")
FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
FB_SCOPE = [
    'email',
    'pages_show_list',
    'instagram_basic',
    'instagram_manage_insights',
        ]
mod_lookup = {'brand': model_db.Brand, 'user': model_db.User}
DEPLOYED_URL = 'https://social-network-255302.appspot.com'
if environ.get('GAE_INSTANCE'):
    URL = DEPLOYED_URL
else:
    environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    URL = 'http://127.0.0.1:8080'


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
        return render_template('index.html', data="Some Arbitrary Words")

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

    @app.route("/callback")
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
        data['token_expires'] = token.get('expires_at')  # TODO: Decide - Should we pass this differently to protect this key?
        data['token'] = token.get('access_token')
        accounts = data.pop('accounts')
        pages = [page.get('id') for page in accounts.get('data')] if accounts and 'data' in accounts else None
        # TODO: Add logic for user w/ many pages/instagram-accounts. Currently assume 1st page is correct one.
        if pages:
            instagram_data = facebook.get(f"https://graph.facebook.com/v4.0/{pages[0]}?fields=instagram_business_account").json()
            ig_id = instagram_data['instagram_business_account'].get('id')
            ig_metric = 'impressions,reach,profile_views'
            ig_period = 'day'
            url = f"https://graph.facebook.com/{ig_id}/insights?metric={ig_metric}&period={ig_period}"
            insights = facebook.get(url).json().get('data')
            url = f"https://graph.facebook.com/v4.0/{ig_id}/media"
            media = facebook.get(url).json().get('data')

            print('================= Instagram Insights!! =================')
            print(media)
            print('------------------------------------------')
            for info in insights:
                print(info)
                # print(info.name, 'Start: ', info.values[0].value, 'End: ', info.values[1].value)
                print('------------------------------------------')
            data['instagram_id'], data['notes'] = ig_id, json.dumps(insights)
        else:
            data['instagram_id'], data['notes'] = None, ''
        print('============== user data collected =====================')
        print(data)
        user = model_db.create(data)
        return redirect(url_for('view', mod='user', id=user['id']))

    @app.route('/<string:mod>/<int:id>')
    def view(mod, id):
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        model = model_db.read(id, Model=Model)
        return render_template('view.html', mod=mod, data=model)

    # @app.route('/insight/<int:id>')
    # def insight(id):
    #     results = ''
    #     return render_template('insight.html', data=results)

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
    def list(mod):
        Model = mod_lookup.get(mod, None)
        if not Model:
            return f"No such route: {mod}", 404
        models = model_db.list(Model=Model)
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
