from os import environ

# class Config:
#     """Flask configuration variables """
SECRET_KEY = environ.get('SECRET_KEY')  # for session cookies & flash messages
SESSION_COOKIE_SECURE = True
REMEMBER_COOKIE_SECURE = True
FB_HOOK_SECRET = environ.get('FB_HOOK_SECRET')
FLASK_APP = environ.get('FLASK_APP')
FLASK_ENV = environ.get('FLASK_ENV')
CAPTURE_BASE_URL = environ.get('CAPTURE_BASE_URL')
CAPTURE_QUEUE = environ.get('CAPTURE_QUEUE')
CAPTURE_SERVICE = environ.get('CAPTURE_SERVICE')
FB_CLIENT_ID = environ.get('FB_CLIENT_ID')
FB_CLIENT_SECRET = environ.get('FB_CLIENT_SECRET')
DEV_RUN = True if environ.get('DEV_RUN') == 'True' else False
GAE_SERVICE = environ.get('GAE_SERVICE')
DEBUG = any([DEV_RUN, environ.get('DEBUG') == 'True', GAE_SERVICE == 'dev'])
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
# Set the following value to the Cloud SQL connection name, e.g.
#   "project:region:cloudsql-instance".
# You must also update the value in app.yaml.
# CLOUDSQL_CONNECTION_NAME = f'{PROJECT_ID}:{PROJECT_REGION}:{CLOUDSQL_INSTANCE}'
CLOUDSQL_CONNECTION_NAME = environ.get('DB_CONNECTION_NAME')
# The CloudSQL proxy is used locally to connect to the cloudsql instance.
# To start the proxy, use:
#   $ cloud_sql_proxy -instances=your-connection-name=tcp:3306
# Port 3306 is the standard MySQL port, but change it if needed.
# Alternatively, you could use a local MySQL instance for testing.
LOCAL_SQLALCHEMY_DATABASE_URI = (
    'mysql+pymysql://{user}:{password}@127.0.0.1:3306/{database}?charset=utf8mb4').format(
        user=CLOUDSQL_USER, password=CLOUDSQL_PASSWORD,
        database=CLOUDSQL_DATABASE)
# When running on App Engine a unix socket is used to connect to the cloudsql instance.
LIVE_SQLALCHEMY_DATABASE_URI = (
    'mysql+pymysql://{user}:{password}@localhost/{database}'
    '?unix_socket=/cloudsql/{connection_name}&charset=utf8mb4').format(
        user=CLOUDSQL_USER, password=CLOUDSQL_PASSWORD,
        database=CLOUDSQL_DATABASE, connection_name=CLOUDSQL_CONNECTION_NAME)
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
    SERVER_NAME = URL.split('//', 1).pop()
    SESSION_COOKIE_DOMAIN = SERVER_NAME
