from flask import Flask
from flask_login import LoginManager
import logging
from .cloud_log import CloudLog, setup_cloud_logging


def create_app(config, debug=None, testing=None, config_overrides=dict()):
    if debug is None:
        debug = config_overrides.get('DEBUG', getattr(config, 'DEBUG', None))
    if testing is None:
        testing = config_overrides.get('TESTING', getattr(config, 'TESTING', None))
    log_client, alert, app_handler = None, None, None
    if not testing:
        base_log_level = logging.DEBUG if debug else logging.INFO
        cloud_log_level = logging.WARNING
        logging.basicConfig(level=base_log_level)  # Ensures a StreamHandler to stderr is attached.
        gae_standard = getattr(config, 'GAE_ENV', None) == 'standard'
        local_env = getattr(config, 'LOCAL_ENV')
        log_name = 'alert'
        cred_path = getattr(config, 'GOOGLE_APPLICATION_CREDENTIALS', None)
        if not gae_standard and not local_env:
            log_client, alert, *ignore = setup_cloud_logging(cred_path, base_log_level, cloud_log_level, extra=log_name)
        else:
            log_client = logging if gae_standard else CloudLog.make_client(credential_path=cred_path)
            alert = CloudLog.make_base_logger(log_name, log_name, base_log_level)
            app_handler = CloudLog.make_handler(CloudLog.APP_HANDLER_NAME, log_client, cloud_log_level)
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = debug
    app.testing = testing
    if config_overrides:
        app.config.update(config_overrides)
    app.log_client = log_client
    app.alert = alert
    if app_handler:
        app.logger.addHandler(app_handler)

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

    return app
