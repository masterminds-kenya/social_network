from os import environ

# class Config:
#     """Flask configuration variables """
# ####### #
# Settings for working with the Graph API (by Facebook for Instagram).
FB_CLIENT_ID = environ.get('FB_CLIENT_ID')
FB_CLIENT_SECRET = environ.get('FB_CLIENT_SECRET')
FB_HOOK_SECRET = environ.get('FB_HOOK_SECRET')
# ####### #
# Settings for Deployment on Google Cloud, and local connection to deployed Database.
PROJECT_NAME = environ.get('PROJECT_NAME')
PROJECT_ID = environ.get('GOOGLE_CLOUD_PROJECT', environ.get('PROJECT_ID', None))
PROJECT_NUMBER = environ.get('PROJECT_NUMBER')
PROJECT_REGION = environ.get('PROJECT_REGION')
PROJECT_ZONE = environ.get('PROJECT_ZONE')
CLOUDSQL_INSTANCE = environ.get('DB_INSTANCE')
CLOUDSQL_USER = environ.get('DB_USER')
CLOUDSQL_PASSWORD = environ.get('DB_PASSWORD')
CLOUDSQL_DATABASE = environ.get('DB_NAME')
GCLOUD_URL = environ.get('URL', environ.get('GCLOUD_URL', ''))
CAPTURE_BASE_URL = environ.get('CAPTURE_BASE_URL')
CAPTURE_QUEUE = environ.get('CAPTURE_QUEUE')
CAPTURE_SERVICE = environ.get('CAPTURE_SERVICE')
# Set the following value to the Cloud SQL connection name, e.g.
#   "project:region:cloudsql-instance".
# You must also update the value in app.yaml.
# CLOUDSQL_CONNECTION_NAME = f'{PROJECT_ID}:{PROJECT_REGION}:{CLOUDSQL_INSTANCE}'
CLOUDSQL_CONNECTION_NAME = environ.get('DB_CONNECTION_NAME')
# When running on App Engine a unix socket is used to connect to the cloudsql instance.
LIVE_SQLALCHEMY_DATABASE_URI = (
    'mysql+pymysql://{user}:{password}@localhost/{database}'
    '?unix_socket=/cloudsql/{connection_name}&charset=utf8mb4').format(
        user=CLOUDSQL_USER, password=CLOUDSQL_PASSWORD,
        database=CLOUDSQL_DATABASE, connection_name=CLOUDSQL_CONNECTION_NAME)
# The CloudSQL proxy is used locally to connect to the cloudsql instance.
# To start the proxy, use:
#   $ cloud_sql_proxy -instances=your-connection-name=tcp:3306
# Port 3306 is the standard MySQL port, but change it if needed.
# Alternatively, you could use a local MySQL instance for testing.
LOCAL_SQLALCHEMY_DATABASE_URI = (
    'mysql+pymysql://{user}:{password}@127.0.0.1:3306/{database}?charset=utf8mb4').format(
        user=CLOUDSQL_USER, password=CLOUDSQL_PASSWORD,
        database=CLOUDSQL_DATABASE)
GAE_SERVICE = environ.get('GAE_SERVICE')
# ####### #
# Flask Settings: Generally for the app, and for running it locally.
SECRET_KEY = environ.get('SECRET_KEY')  # for session cookies & flash messages
FLASK_APP = environ.get('FLASK_APP')
FLASK_ENV = environ.get('FLASK_ENV', 'production')
DEV_RUN = True if environ.get('DEV_RUN') == 'True' else False
DEBUG = any([DEV_RUN, environ.get('DEBUG') == 'True', GAE_SERVICE == 'dev'])
LOCAL_URL = 'http://127.0.0.1:8080'
if FLASK_APP and FLASK_ENV:
    LOCAL_URL = 'http://127.0.0.1:5000'
if environ.get('GAE_INSTANCE'):
    SQLALCHEMY_DATABASE_URI = LIVE_SQLALCHEMY_DATABASE_URI
    URL = GCLOUD_URL
    LOCAL_ENV = False
else:
    SQLALCHEMY_DATABASE_URI = LOCAL_SQLALCHEMY_DATABASE_URI
    environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    URL = LOCAL_URL
    LOCAL_ENV = True
SESSION_COOKIE_SECURE = True
REMEMBER_COOKIE_SECURE = True
if LOCAL_ENV:
    SERVER_NAME = URL.split('//', 1).pop()
    SESSION_COOKIE_DOMAIN = SERVER_NAME
    JSONIFY_PRETTYPRINT_REGULAR = True  # default is True on DEBUG, False on PRODUCTION.
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
EXPLAIN_TEMPLATE_LOADING = False  # Creates info log with verbose template loading process. default is False.
# SESSION_COOKIE_NAME = 'bacchus-session'
REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True  # keep user cookie up-to-date with each request.
# PREFERRED_URL_SCHEME = 'https' or 'http'
