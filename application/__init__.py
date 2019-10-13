# import logging
from flask import Flask, render_template, abort, request, redirect, url_for  # , current_app
from . import model_db
import requests_oauthlib
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
from os import environ

FB_CLIENT_ID = environ.get("FB_CLIENT_ID")
FB_CLIENT_SECRET = environ.get("FB_CLIENT_SECRET")
FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
FB_SCOPE = [
    'email',
    'instagram_basic',
    'instagram_manage_insights',
        ]

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
        return render_template('index.html', data="Some Arbitrary Data")

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
        token = facebook.fetch_token(FB_TOKEN_URL, client_secret=FB_CLIENT_SECRET, authorization_response=request.url,).json()
        if 'error' in token:
            return token, 500
        # Fetch a protected resources:
        facebook_user_data = facebook.get("https://graph.facebook.com/me?fields=id,name,email,accounts").json()
        if 'error' in facebook_user_data:
            return facebook_user_data, 500
        # TODO: use a better constructor for the user account.
        data = facebook_user_data.copy()  # .to_dict(flat=True)
        data['token_expires'] = token.get('expires_at')  # TODO: Decide - Should we pass this differently to protect this key?
        data['token'] = token.get('access_token')
        accounts = data.pop('accounts')
        pages = [page.get('id') for page in accounts.get('data')] if accounts and 'data' in accounts else None
        # TODO: Add logic for user w/ many pages/instagram-accounts. Currently assume 1st page is correct one.
        if pages:
            instagram_data = facebook.get(f"https://graph.facebook.com/v4.0/{pages[0]}?fields=instagram_business_account").json()
            data['instagram_id'] = instagram_data['instagram_business_account'].get('id')
        else:
            data['instagram_id'] = None
        print('============== instagram_id =====================')
        print(data)
        user = model_db.create(data)
        return redirect(url_for('view', id=user['id']))

    @app.route('/user/<int:id>')
    def view(id):
        # model = model_db.User
        user = model_db.read(id)
        return render_template('view.html', model='User', data=user)

    @app.route('/brand/<int:id>')
    def brand_view(id):
        Model = model_db.Brand
        brand = model_db.read(id, Model=Model)
        return render_template('view.html', model='Brand', data=brand)

    @app.route('/user/add', methods=['GET', 'POST'])
    def add():
        if request.method == 'POST':
            data = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
            user = model_db.create(data)
            return redirect(url_for('view', id=user['id']))
        return render_template('user_form.html', action='Add', user={})

    @app.route('/brand/add', methods=['GET', 'POST'])
    def brand_add():
        Model = model_db.Brand
        if request.method == 'POST':
            data = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
            brand = model_db.create(data, Model=Model)
            return redirect(url_for('brand_view', id=brand['id']))
        return render_template('brand_form.html', action='Add', brand={})

    @app.route('/user/<int:id>/edit', methods=['GET', 'POST'])
    def edit(id):
        user = model_db.read(id)
        if request.method == 'POST':
            data = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
            user = model_db.update(data, id)
            return redirect(url_for('view', id=user['id']))
        return render_template('user_form.html', action='Edit', user=user)

    @app.route('/user/<int:id>/delete')
    def delete(id):
        model_db.delete(id)
        return redirect(url_for('home'))

    @app.route('/user/list')
    def list():
        users = model_db.list()
        return render_template('list.html', users=users)

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
        print(e)
        return """
        An internal error occurred: <pre>{}</pre>
        See logs for full stacktrace.
        """.format(e), 500

    return app
