from flask import Flask
from flask_login import LoginManager
from google.cloud import logging as cloud_logging
import logging
from .cloud_log import CloudLog
import google.auth


def create_app(config, debug=None, testing=None, config_overrides=dict()):

    print("============ Google Auth Discovery: BEGIN ==========================")
    credentials, project_id = google.auth.default()
    reload = getattr(config, 'FLASK_RUN_RELOAD', 'RELOAD NOT SET')
    print(f"Project ID: {project_id} ")
    print(f"Credentials: {credentials} ")
    print(f"Reload: {reload} ")
    print("============ Google Auth Discovery: END ==========================")
    if debug is None:
        source = config_overrides if 'DEBUG' in config_overrides else config
        debug = getattr(source, 'DEBUG', None)
    if testing is None:
        source = config_overrides if 'TESTING' in config_overrides else config
        getattr(source, 'TESTING', None)
    log_client, alert = None, None
    if not testing:
        base_log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=base_log_level)
        cloud_log_level = logging.WARNING
        base_log = logging.getLogger(__name__)
        print("================ CLOUD LOG CLIENT =======================")
        log_client = cloud_logging.Client(credentials=credentials)
        print("----------- MAKE (not add) CLOUD HANDLER -------------------------")
        base_log.addHandler(CloudLog.make_cloud_handler('app', log_client, level=cloud_log_level))
        print("----------- make CloudLog instance -------------------------")
        alert = CloudLog('alert', 'alert', base_log_level, log_client)
    print("-------------- MAKE FLASK APP ----------------------")
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = debug
    app.testing = testing
    app.log_client = log_client
    app.alert = alert
    if config_overrides:
        app.config.update(config_overrides)

    # Configure flask_login
    login_manager = LoginManager()
    login_manager.login_view = 'signup'  # where to find the login route
    login_manager.login_message = "Join the platform, or click login to use your existing account. "
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return model_db.User.query.get(int(user_id))

    # Setup the data model. Import routes and events.
    with app.app_context():
        from . import model_db
        from . import routes  # noqa: F401
        model_db.init_app(app)
        from . import events  # noqa: F401

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error('================== Error Handler =====================')
        app.logger.error(e)
        if app.config.get('DEBUG'):
            return """
            An internal error occurred: <pre>{}</pre>
            See logs for full stacktrace.
            """.format(e), 500
        else:
            return "An internal error occurred. Contact admin. ", 500
    print("======================= FINISH AND RETURN APP ================================")
    return app
