from os import environ


class Config:
    """Flask configuration variables and application settings. """
    # Environment Parameters for Local, Dev, or Production.
    GAE_ENV = environ.get('GAE_ENV')  # expected: standard
    GAE_SERVICE = environ.get('GAE_SERVICE')  # 'dev', 'default', 'capture', etc.
    GAE_INSTANCE = environ.get('GAE_INSTANCE')
    GAE_VERSION = environ.get('GAE_VERSION')  # source code version on GCloud.
    GAE_FLEX_PROJECT = environ.get("GCLOUD_PROJECT")   # GAE - flex environment.
    GAE_STANDARD_PROJECT = environ.get("GOOGLE_CLOUD_PROJECT")  # GAE - stanard (v2) environment.
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
    PROJECT = GAE_STANDARD_PROJECT or GAE_FLEX_PROJECT
    PROJECT_ID = environ.get('PROJECT_ID')  # As set by developer in environment variables.
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
    add_to_dict = ('PROJECT_ID', 'PROJECT_ZONE', 'GAE_SERVICE', 'GAE_ENV')

    def __init__(self) -> None:
        self.LOCAL_ENV = self.get_LOCAL_ENV()
        self.CODE_SERVICE = self.get_CODE_SERVICE()
        self.URL = self.get_URL()
        self.SQLALCHEMY_DATABASE_URI = self.get_SQLALCHEMY_DATABASE_URI()
        for key in self.add_to_dict:
            setattr(self, key, getattr(self, key, None))
        if self.LOCAL_ENV:
            self.SERVER_NAME = self.URL.split('//', 1).pop()
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

    @property
    def standard_env(self):
        """Returns boolean for the environment is 'GAE Standard', or running local. """
        expected = ('local', 'standard')
        code_environment = 'local' if self.LOCAL_ENV else self.GAE_ENV
        if code_environment in expected:
            return True
        return False

    def get_LOCAL_ENV(self):
        """Currently assumes either it is running on GAE or it is local. """
        if self.GAE_INSTANCE:
            return False
        return True

    def get_CODE_SERVICE(self):
        """Returns a str representing the environment the app is running on. """
        code_service = 'local' if self.LOCAL_ENV else self.GAE_SERVICE
        return code_service.lower()

    def get_GCLOUD_URL(self):
        """On GCP the default URL is computed from the 'service', 'project_id', and 'project_region'. """
        service_string = ''
        if self.GAE_SERVICE not in (None, 'default'):
            service_string = self.GAE_SERVICE + '-dot-'
        return f'https://{service_string}{self.PROJECT_ID}.{self.PROJECT_REGION}.r.appspot.com'

    def get_URL(self):
        """Returns the appropriate URL depending on the context of where the code is running. """
        if self.LOCAL_ENV:
            LOCAL_URL = 'http://127.0.0.1:5000' if self.FLASK_APP and self.FLASK_ENV else 'http://127.0.0.1:8080'
            return LOCAL_URL
        return self.URL_SETTING or self.get_GCLOUD_URL()

    def get_DB_CLOUD_CONNECTION(self):
        """Part of the path string for database connection when running on GCP, using the expected unix socket for GAE.
        The DB_CONNECTION_NAME should be in the format of 'project:region:cloudsql-instance'.
        The deployment 'app.yaml' (and similar) file should be updated with the needed values.
        """
        db_connection = self.DB_CONNECTION_NAME
        if not db_connection:
            params = (self.PROJECT_ID, self.PROJECT_REGION, self.DB_INSTANCE)
            if not all(params):
                raise ValueError(f"Must have either a DB_CONNECTION_NAME, or all of {', '.join(params)}. ")
            db_connection = ':'.join(params)
        return f'localhost/{self.DB_NAME}?unix_socket=/cloudsql/{db_connection}&'

    def get_DB_LOCAL_CONNECTION(self):
        """Part of the path string - used for running locally but connecting to the database via CloudSQL proxy.
        The MySQL default port is 3306, but change it if needed.
        When running locally, start the proxy from a terminal using:
            cloud_sql_proxy -instances=your-connection-name=tcp:3306
        Alternatively, can use a local MySQL instance for testing.
        """
        db_port = getattr(self, 'DB_PORT', '3306')
        return f'127.0.0.1:{db_port}/{self.DB_NAME}?'

    def get_SQLALCHEMY_DATABASE_URI(self):
        """Returns a context specific (running locally or on GAE) for connecting to the database.
        Expected on GAE:
            'mysql+pymysql://{user}:{password}@localhost/{db_name}'
            '?unix_socket=/cloudsql/{connection_name}&charset=utf8mb4'
        Expected for local with CloudSQL proxy connection:
            'mysql+pymysql://{user}:{password}@127.0.0.1:3306/{database}?charset=utf8mb4'
        """
        db_string = self.get_DB_LOCAL_CONNECTION() if self.LOCAL_ENV else self.get_DB_CLOUD_CONNECTION()
        return f'mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{db_string}charset=utf8mb4'
