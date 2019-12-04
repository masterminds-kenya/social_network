import logging
from flask import Flask  # , render_template, abort, request, flash, redirect, url_for  # , current_app
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
