from flask import Flask
from flask_login import LoginManager
import logging
from .cloud_log import CloudLog, LowPassFilter, setup_cloud_logging  # , StructHandler, TempLog, CloudHandler

NEVER_CLOUDLOG = False
FORCE_CLOUDlOG = True


def create_app(config, debug=None, testing=None, config_overrides=dict()):
    if debug is None:
        debug = config_overrides.get('DEBUG', getattr(config, 'DEBUG', None))
    if testing is None:
        testing = config_overrides.get('TESTING', getattr(config, 'TESTING', None))
    log_client, alert, app_handler, root_handler, c_log, c_res, s_log = None, None, None, None, None, None, None
    if not testing:
        base_log_level = logging.DEBUG if debug else logging.INFO
        cloud_log_level = logging.WARNING
        logging.basicConfig(level=base_log_level)  # Ensures a StreamHandler to stderr is attached.
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
            alert = CloudLog.make_base_logger(log_name, log_name, base_log_level, None, _res, log_client)
            c_log = CloudLog('c_log', base_log_level, None, None, log_client)
            c_resource = CloudLog.make_resource(config, res_type='logging_log', name='c_res')
            # c_res = CloudLog('c_res', base_log_level, None, c_resource, log_client)
            app_handler = CloudLog.make_handler(CloudLog.APP_HANDLER_NAME, cloud_log_level, None, test, log_client)
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
    app.c_log = c_log
    app.c_res = c_res
    app.s_log = s_log
    app.log_list = ['alert', 'c_log', 'c_res', 's_log']
    if app_handler:
        app.logger.addHandler(app_handler)
        low_filter = LowPassFilter(app.logger.name, cloud_log_level)
        root_handler = logging.root.handlers[0]
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
