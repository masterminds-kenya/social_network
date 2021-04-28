from flask import Flask
from flask_login import LoginManager
from google.cloud import logging as cloud_logging
import logging
from .cloud_log import CloudLog
# from google.auth import default as auth_default


def create_app(config, debug=None, testing=None, config_overrides=dict()):
    if debug is None:
        debug = config_overrides.get('DEBUG', getattr(config, 'DEBUG', None))
    if testing is None:
        testing = config_overrides.get('TESTING', getattr(config, 'TESTING', None))
    log_client, alert, cloud_log_level = None, None, None
    if not testing:
        base_log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=base_log_level)
        cloud_log_level = logging.WARNING
        logging.basicConfig(level=base_log_level)  # Ensures a StreamHandler to stderr is attached.
        log_client = cloud_logging.Client()
        log_client.setup_logging(log_level=base_log_level)  # log_level sets the logger, not the handler.
        logging.root.addHandler(CloudLog.make_cloud_handler('app', log_client, level=cloud_log_level))
        alert = CloudLog('alert', 'alert', base_log_level, log_client)
    print("========== MAKE APP =====================")
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

    app.logger.debug("============ Setup Report =========================\n")
    print('Root Handlers: ', logging.root.handlers)
    print('App Logger Handlers: ', app.logger.handlers)
    print('--------------- move them ---------------------')
    CloudLog.move_handlers(logging.root, app.logger, log_level=cloud_log_level)
    print('Root Handlers: ', logging.root.handlers)
    print('App Logger Handlers: ', app.logger.handlers)
    print('---------------- CloudLog Logger Tests -------------------')
    CloudLog.test_loggers(app, ['alert'])
    # handler = log_client.get_default_handler()
    # handler.level = cloud_log_level  # Lower logger levels go out standard, higher go to special tracking.
    # print(handler)

    # # app.logger.debug(f"Project ID: {project_id} ")
    # app.logger.debug(f"Credentials: {credentials} ")
    # app.logger.debug(credentials.expired)
    # app.logger.debug(credentials.valid)
    # app.logger.debug("--------------------------------------------------")
    # app.logger.debug(credentials.__dict__)
    # app.logger.debug("--------------------------------------------------")
    app.logger.debug("----------------- App Log Client Credentials ---------------------")
    log_creds = log_client._credentials if log_client else None
    if log_creds:
        app.logger.debug(f"App Log Client Creds: {log_creds} ")
        app.logger.debug(log_creds.expired)
        app.logger.debug(log_creds.valid)
        app.logger.debug("--------------------------------------------------")
        app.logger.debug(log_creds.__dict__)
    else:
        app.logger.debug("Log Creds not found. ")
    app.logger.debug("--------------------------------------------------")

    print("======================= FINISH AND RETURN APP ================================")
    return app
