from flask import Flask
from flask_login import LoginManager
import logging
from google.cloud import logging as google_logging
# from google.cloud.logging.resource import Resource
# from google.cloud.logging.handlers import CloudLoggingHandler, setup_logging


def create_app(config, debug=False, testing=False, config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = getattr(config, 'DEBUG') or debug
    app.testing = getattr(config, 'TESTING', None) or testing
    if config_overrides:
        app.config.update(config_overrides)
    # Configure logging depth: ?NOTSET?, DEBUG, INFO, WARNING, ERROR, CRITICAL
    if not app.testing:
        # log_level = logging.DEBUG if app.debug else logging.INFO
        # logging.basicConfig(level=log_level)
        log_client = google_logging.Client()
        log_name = 'daily_download'
        daily_log = log_client.logger(log_name)
        app.glog = log_client
        app.daily_log = daily_log

        # resource_type = 'generic_task'
        # resource = Resource(
        #     type=resource_type,
        #     labels={
        #         'service_name': app.config.GAE_SERVICE,
        #         'location': app.config.PROJECT_REGION,
        #     })
        # struct = {
        #     'content': 'Initial Content. '
        # }

        # daily_log.log_struct(struct, resource=resource, severity='INFO')
        # client.get_default_handler()
        # client.setup_logging(log_level=log_level)
        # handler = CloudLoggingHandler(client)
        # logging.getLogger().setLevel(log_level)
        # setup_logging(handler)
        logging.info('Root logging message. ')
        app.logger.info('App logging. ')

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
