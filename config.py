from os import environ


class Config:
    """Flask configuration variables and application settings. """
    # ####### #
    # Environment Parameters for Local, Dev, or Production.
    GAE_SERVICE = environ.get('GAE_SERVICE')
    GAE_INSTANCE = environ.get('GAE_INSTANCE')
    URL_SETTING = environ.get('URL')
    # General Flask Settings
    SECRET_KEY = environ.get('SECRET_KEY')  # for session cookies & flash messages
    FLASK_APP = environ.get('FLASK_APP')
    FLASK_ENV = environ.get('FLASK_ENV', 'production')
    DEV_RUN = True if environ.get('DEV_RUN') == 'True' else False
    DEBUG = any([DEV_RUN, environ.get('DEBUG') == 'True', GAE_SERVICE == 'dev'])
    EXPLAIN_TEMPLATE_LOADING = False  # Creates info log with verbose template loading process. default is False.
    # SESSION_COOKIE_NAME = 'bacchus-session'
    # PREFERRED_URL_SCHEME = 'https' or 'http'
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True  # keep user cookie up-to-date with each request.
    # Settings for working with the Graph API (by Facebook for Instagram).
    FB_CLIENT_ID = environ.get('FB_CLIENT_ID')
    FB_CLIENT_SECRET = environ.get('FB_CLIENT_SECRET')
    FB_HOOK_SECRET = environ.get('FB_HOOK_SECRET')
    # Settings for Deployment on Google Cloud, and local/deployed connection to deployed Database.
    PROJECT_NAME = environ.get('PROJECT_NAME')
    PROJECT_ID = environ.get('GOOGLE_CLOUD_PROJECT', environ.get('PROJECT_ID', None))
    PROJECT_NUMBER = environ.get('PROJECT_NUMBER')
    PROJECT_REGION = environ.get('PROJECT_REGION')
    PROJECT_ZONE = environ.get('PROJECT_ZONE')
    DB_USER = environ.get('DB_USER')
    DB_PASSWORD = environ.get('DB_PASSWORD')
    DB_NAME = environ.get('DB_NAME')
    DB_INSTANCE = environ.get('DB_INSTANCE')
    DB_CONNECTION_NAME = environ.get('DB_CONNECTION_NAME')
    # Parameters for Application Features
    CAPTURE_BASE_URL = environ.get('CAPTURE_BASE_URL')
    CURRENT_SERVICE = environ.get('GAE_SERVICE', 'dev')
    CAPTURE_SERVICE = environ.get('CAPTURE_SERVICE')
    COLLECT_SERVICE = environ.get('COLLECT_SERVICE', environ.get('GAE_SERVICE', 'dev'))
    CAPTURE_QUEUE = environ.get('CAPTURE_QUEUE')
    COLLECT_QUEUE = environ.get('COLLECT_QUEUE')

    def __init__(self) -> None:
        self.LOCAL_ENV = self.get_LOCAL_ENV()
        self.CODE_ENVIRONMENT = 'LOCAL' if self.LOCAL_ENV else self.GAE_SERVICE
        self.URL = self.get_URL()
        self.SQLALCHEMY_DATABASE_URI = self.get_SQLALCHEMY_DATABASE_URI()
        self.SERVER_NAME = self.URL.split('//', 1).pop()
        if self.LOCAL_ENV:
            self.SESSION_COOKIE_DOMAIN = self.SERVER_NAME
            self.JSONIFY_PRETTYPRINT_REGULAR = True  # default is True on DEBUG, False on PRODUCTION.
            self.SESSION_COOKIE_SECURE = False
            self.REMEMBER_COOKIE_SECURE = False
            if self.DEBUG:
                self.FLASK_RUN_RELOAD = False
        else:
            environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
            self.SESSION_COOKIE_SECURE = True
            self.REMEMBER_COOKIE_SECURE = True
        GOOGLE_APPLICATION_CREDENTIALS = environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if GOOGLE_APPLICATION_CREDENTIALS:
            self.GOOGLE_APPLICATION_CREDENTIALS = GOOGLE_APPLICATION_CREDENTIALS

    def get_LOCAL_ENV(self):
        return not self.GAE_INSTANCE

    def get_GCLOUD_URL(self):
        service_string = ''
        if self.GAE_SERVICE not in (None, 'default'):
            service_string = self.GAE_SERVICE + '-dot-'
        return f'https://{service_string}{self.PROJECT_ID}.{self.PROJECT_REGION}.r.appspot.com'

    def get_URL(self):
        if self.LOCAL_ENV:
            LOCAL_URL = 'http://127.0.0.1:5000' if self.FLASK_APP and self.FLASK_ENV else 'http://127.0.0.1:8080'
            return LOCAL_URL
        return self.URL_SETTING or self.get_GCLOUD_URL()

    def get_DB_CLOUD_CONNECTION(self):
        # Set the following value to the Cloud SQL connection name, e.g.
        #   "project:region:cloudsql-instance".
        # You must also update the value in app.yaml.
        # When running on App Engine a unix socket is used to connect to the cloudsql instance.
        db_connection = self.DB_CONNECTION_NAME
        if not db_connection:
            params = (self.PROJECT_ID, self.PROJECT_REGION, self.DB_INSTANCE)
            if not all(params):
                raise ValueError(f"Must have either a DB_CONNECTION_NAME, or all of {', '.join(params)}. ")
            db_connection = ':'.join(params)
        return f'localhost/{self.DB_NAME}?unix_socket=/cloudsql/{db_connection}&'

    def get_DB_LOCAL_CONNECTION(self):
        # The CloudSQL proxy is used locally to connect to the cloudsql instance.
        # To start the proxy, use:
        #   $ cloud_sql_proxy -instances=your-connection-name=tcp:3306
        # Port 3306 is the standard MySQL port, but change it if needed.
        # Alternatively, you could use a local MySQL instance for testing.
        return f'127.0.0.1:3306/{self.DB_NAME}?'

    def get_SQLALCHEMY_DATABASE_URI(self):
        db_string = self.get_DB_LOCAL_CONNECTION() if self.LOCAL_ENV else self.get_DB_CLOUD_CONNECTION()
        # LIVE_SQLALCHEMY_DATABASE_URI = (
        #     'mysql+pymysql://{user}:{password}@localhost/{database}'
        #     '?unix_socket=/cloudsql/{connection_name}&charset=utf8mb4').format(
        #         user=user, password=password,
        #         database=db_name, connection_name=connection_name)
        # LOCAL_SQLALCHEMY_DATABASE_URI = (
        #     'mysql+pymysql://{user}:{password}@127.0.0.1:3306/{database}?charset=utf8mb4').format(
        #         user=user, password=password,
        #         database=db_name)
        # return LOCAL_SQLALCHEMY_DATABASE_URI if self.LOCAL_ENV else LIVE_SQLALCHEMY_DATABASE_URI
        return f'mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{db_string}charset=utf8mb4'
