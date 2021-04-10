from flask import Flask
from flask_login import LoginManager
import logging
from .cloud_log import log_setup


def create_app(config, debug=False, testing=False, config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = getattr(config, 'DEBUG') or debug
    app.testing = getattr(config, 'TESTING', None) or testing
    if config_overrides:
        app.config.update(config_overrides)
    if not app.testing:
        log_level = logging.DEBUG if app.debug else logging.INFO
        log_type = 'BASIC'
        g_log = log_setup(log_type, log_level)

        logging.info('Root logging message. ')
        app.logger.info('App logging. ')
        g_log.info('Constructed Logger Info. ')
        # app.alert.info('Alert logging info. ')

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
