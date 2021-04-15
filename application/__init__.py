from flask import Flask
from flask_login import LoginManager
from google.cloud import logging as cloud_logging
import logging
from .cloud_log import CloudLog


def create_app(config, debug=False, testing=False, config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = debug or getattr(config, 'DEBUG', None)
    app.testing = testing or getattr(config, 'TESTING', None)
    if config_overrides:
        app.config.update(config_overrides)
    if not app.testing:
        base_log_level = logging.DEBUG if app.debug else logging.INFO
        cloud_log_level = logging.WARNING
        logging.basicConfig(level=base_log_level)
        base_log = logging.getLogger(__name__)
        log_client = cloud_logging.Client()
        base_log.addHandler(CloudLog.make_cloud_handler('LOG', log_client))
        app.log_client = log_client
        app.app_log = CloudLog.create_logger(__name__, 'LOG', base_log_level, log_client)
        app.alert = CloudLog('ALERT', 'alert', cloud_log_level, log_client)

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
