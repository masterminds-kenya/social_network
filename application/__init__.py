import logging
from flask import Flask
from flask_login import LoginManager
from . import model_db


def create_app(config, debug=False, testing=False, config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = debug
    app.testing = testing
    if config_overrides:
        app.config.update(config_overrides)
    # Configure logging
    if not app.testing:
        logging.basicConfig(level=logging.INFO)
    # Configure flask_login
    login_manager = LoginManager()
    login_manager.login_view = 'login'  # where to find the login route
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return model_db.User.query.get(int(user_id))

    # Setup the data model.
    with app.app_context():
        from . import routes  # noqa: F401
        model = model_db
        model.init_app(app)

    # Routes

    # TODO: For production, the output of the error should be disabled.
    @app.errorhandler(500)
    def server_error(e):
        app.logger.error('================== Error Handler =====================')
        app.logger.error(e)
        return """
        An internal error occurred: <pre>{}</pre>
        See logs for full stacktrace.
        """.format(e), 500

    return app
