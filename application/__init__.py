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
    'user_link',
    'user_friends',
    'user_likes',
    'user_photos',
    'user_posts',
    'user_tagged_places',
    'user_videos',
    'groups_access_member_info',
    'pages_show_list',
    'read_insights',
    'instagram_basic',
    'instagram_manage_comments',
    'instagram_manage_insights',
        ]
URL = ''


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
        facebook = requests_oauthlib.OAuth2Session(
            FB_CLIENT_ID, redirect_uri=URL + '/callback', scope=FB_SCOPE
        )
        authorization_url, _ = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)
        return redirect(authorization_url)

    @app.route("/callback")
    def callback():
        facebook = requests_oauthlib.OAuth2Session(
            FB_CLIENT_ID, scope=FB_SCOPE, redirect_uri=URL + "/fb-callback"
        )
        # we need to apply a fix for Facebook here
        facebook = facebook_compliance_fix(facebook)
        facebook.fetch_token(
            FB_TOKEN_URL,
            client_secret=FB_CLIENT_SECRET,
            authorization_response=request.url,
        )
        # Fetch a protected resource, i.e. user profile, via Graph API
        facebook_user_data = facebook.get(
            "https://graph.facebook.com/me?fields=id,name,email,picture{url}"
        ).json()
        email = facebook_user_data['email']
        name = facebook_user_data['name']
        picture_url = facebook_user_data.get('picture', {}).get('data', {}).get('url')
        return f"""
        User information: <br>
        Name: {name} <br>
        Email: {email} <br>
        Avatar <img src="{picture_url}"> <br>
        <a href="/">Home</a>
        """

    @app.route('/user/<int:id>')
    def view(id):
        user = model_db.read(id)
        return render_template('view.html', user=user)

    @app.route('/user/add', methods=['GET', 'POST'])
    def add():
        if request.method == 'POST':
            data = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
            data['admin'] = True if 'admin' in data.keys() and data['admin'] == 'on' else False
            user = model_db.create(data)
            return redirect(url_for('view', id=user['id']))
        return render_template('user_form.html', action='Add', user={})

    @app.route('/user/<int:id>/edit', methods=['GET', 'POST'])
    def edit(id):
        user = model_db.read(id)
        if request.method == 'POST':
            data = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
            data['admin'] = True if 'admin' in data and data['admin'] == 'on' else False
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
