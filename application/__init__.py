from flask import Flask
from flask_login import LoginManager
import logging
from .cloud_log import CloudHandler, CloudLog, LowPassFilter, setup_cloud_logging, StructHandler

NEVER_CLOUDLOG = False
FORCE_CLOUDlOG = False


def create_app(config, debug=None, testing=None, config_overrides=dict()):
    if debug is None:
        debug = config_overrides.get('DEBUG', getattr(config, 'DEBUG', None))
    if testing is None:
        testing = config_overrides.get('TESTING', getattr(config, 'TESTING', None))
    log_client, alert, app_handler, root_handler, s_log, c_log, res_c = None, None, None, None, None, None, None
    if not testing:
        base_log_level = logging.DEBUG if debug else logging.INFO
        cloud_log_level = logging.WARNING
        logging.basicConfig(level=base_log_level)  # Ensures a StreamHandler to stderr is attached.
        if len(logging.root.handlers):
            root_handler = logging.root.handlers[0]
            formatter = root_handler.formatter
        else:
            formatter = CloudLog.make_formatter()
        log_name = 'alert'
        cred_path = getattr(config, 'GOOGLE_APPLICATION_CREDENTIALS', None)
        if not config.standard_env:
            log_client, alert, *ignore = setup_cloud_logging(cred_path, base_log_level, cloud_log_level, extra=log_name)
        else:
            if NEVER_CLOUDLOG or (not FORCE_CLOUDlOG and getattr(config, 'GAE_ENV', None) == 'standard'):
                log_client = logging
                _res, test = None, None
            else:
                log_client = CloudLog.make_client(cred_path)
                _res = None
                test = None
                # test = CloudLog.make_resource(config, res_type='logging_log', name=CloudLog.APP_HANDLER_NAME)
            alert = CloudLog.make_base_logger(log_name, log_name, log_client, base_log_level, formatter, _res)
            # alert = TempLog(log_name, log_name, None, base_log_level, formatter)
            c_log = CloudLog('c_log', base_log_level, formatter, None, log_client)
            c_resource = CloudLog.make_resource(config, res_type='logging_log', name='c_res')
            c_res = CloudLog('c_res', log_client, base_log_level, formatter, c_resource, log_client)
            # s_log = logging.getLogger('s_log')
            # s_handler = StructHandler('s_log', base_log_level, formatter)
            # s_log.addHandler(s_handler)
            # s_log.propagate = False
            alert.propagate = False
            c_log.propagate = False
            c_res.propagate = False
            app_handler = CloudLog.make_handler(CloudLog.APP_HANDLER_NAME, cloud_log_level, formatter, test, log_client)
            test = c_resource
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = debug
    app.testing = testing
    if config_overrides:
        app.config.update(config_overrides)
    app.log_client = log_client
    app._resource_test = test
    app.alert = alert
    app.s_log = s_log
    app.c_log = c_log
    app.res_c = res_c
    app.log_list = ['alert', 's_log', 'c_log', 'res_c']
    if app_handler:
        app.logger.addHandler(app_handler)
        if root_handler:
            low_filter = LowPassFilter(app.logger.name, cloud_log_level)
            root_handler.addFilter(low_filter)

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
