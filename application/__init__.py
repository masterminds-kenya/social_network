from flask import Flask
from flask_login import LoginManager
import logging
from .cloud_log import CloudLog, LowPassFilter, setup_cloud_logging  # , StructHandler, TempLog, CloudHandler


def create_app(config, debug=None, testing=None, config_overrides=dict()):
    if debug is None:
        debug = config_overrides.get('DEBUG', getattr(config, 'DEBUG', None))
    if testing is None:
        testing = config_overrides.get('TESTING', getattr(config, 'TESTING', None))
    if not testing:
        base_log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=base_log_level)  # Ensures a StreamHandler to stderr is attached.
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = debug
    app.testing = testing
    if config_overrides:
        app.config.update(config_overrides)

    @app.before_first_request
    def attach_cloud_loggers():
        build = ' First Request on Build: {} '.format(app.config.get('GAE_VERSION', 'UNKNOWN VERSION'))
        logging.info('{:*^74}'.format(build))
        cloud_level = logging.WARNING
        log_client, alert, app_handler, c_log, res = None, None, None, None, None
        if not testing:
            base_level = logging.DEBUG if debug else logging.INFO
            log_name = 'alert'
            cred_path = getattr(config, 'GOOGLE_APPLICATION_CREDENTIALS', None)
            if not config.standard_env:
                log_client, alert, *skip = setup_cloud_logging(cred_path, base_level, cloud_level, config, log_name)
            else:
                try:
                    log_client = CloudLog.make_client(cred_path)
                except Exception as e:
                    logging.exception(e)
                    log_client = logging
                # res = CloudLog.make_resource(config, fancy='I am')  # TODO: fix passing a created resource.
                alert = CloudLog(log_name, base_level, res, log_client)
                c_log = CloudLog('c_log', base_level, res, logging)
                # c_log = CloudLog.make_base_logger('c_log', base_level, res, log_client)
                app_handler = CloudLog.make_handler(CloudLog.APP_HANDLER_NAME, cloud_level, res, log_client)
        app.log_client = log_client
        app._resource_test = res
        app.alert = alert
        app.c_log = c_log
        app.log_list = ['alert', 'c_log']
        if app_handler:
            app.logger.addHandler(app_handler)
            if log_client is logging:
                low_filter = LowPassFilter(app.logger.name, cloud_level)
                root_handler = logging.root.handlers[0]
                root_handler.addFilter(low_filter)
        logging.debug("***************************** END PRE-REQUEST ************************************")

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
