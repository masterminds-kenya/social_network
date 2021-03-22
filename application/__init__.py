import logging
from flask import Flask
from flask_login import LoginManager

# from google.cloud import logging as g_log
# logging_client = g_log.Client()
# log_name = "my-log"  # The name of the log to write to
# logger = logging_client.logger(log_name)  # Selects the log to write to
# text = "Hello, world!"  # The data to log
# logger.log_text(text)  # Writes the log entry
# print("Logged: {}".format(text))

# # FROM: https://cloud.google.com/logging/docs/setup/python
# import google.cloud.logging  # Imports the Cloud Logging client library
# client = google.cloud.logging.Client()  # Instantiates a client

# # Retrieves a Cloud Logging handler based on the environment
# # you're running in and integrates the handler with the
# # Python logging module. By default this captures all logs
# # at INFO level and higher
# client.get_default_handler()
# client.setup_logging()
# import logging  # Imports Python standard library logging
# text = "Hello, world!"  # The data to log
# logging.warning(text)  # Emits the data using the standard logging module

# FROM: https://googleapis.dev/python/logging/latest/stdlib-usage.html
# import logging
# import google.cloud.logging # Don't conflict with standard logging
# from google.cloud.logging.handlers import CloudLoggingHandler
# client = google.cloud.logging.Client()
# handler = CloudLoggingHandler(client)
# cloud_logger = logging.getLogger('cloudLogger')
# cloud_logger.setLevel(logging.INFO)  # defaults to WARN
# cloud_logger.addHandler(handler)
# cloud_logger.error('bad news')
# handler = CloudLoggingHandler(client, name="mycustomlog")

# Also possible to attach the handler to the root Pythong logger.
# import logging
# import google.cloud.logging # Don't conflict with standard logging
# from google.cloud.logging.handlers import CloudLoggingHandler, setup_logging
# client = google.cloud.logging.Client()
# handler = CloudLoggingHandler(client)
# logging.getLogger().setLevel(logging.INFO) # defaults to WARN
# setup_logging(handler)
# logging.error('bad news')


def create_app(config, debug=False, testing=False, config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = getattr(config, 'DEBUG') or debug
    app.testing = getattr(config, 'TESTING', None) or testing
    if config_overrides:
        app.config.update(config_overrides)
    # Configure logging depth: ?NOTSET?, DEBUG, INFO, WARNING, ERROR, CRITICAL
    if not app.testing:
        log_level = logging.DEBUG if app.debug else logging.INFO
        logging.basicConfig(level=log_level)
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
