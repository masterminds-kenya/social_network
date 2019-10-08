# import logging
from flask import Flask, render_template, abort  # , redirect, url_for, current_app
from . import model_db


def create_app(config, debug=False, testing=False, config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(config)
    app.debug = debug
    app.testing = testing
    if config_overrides:
        app.config.update(config_overrides)
    # # Configure logging
    # if not app.testing:
    #     logging.basicConfig(level=logging.INFO)
    # Setup the data model.
    with app.app_context():
        model = model_db
        model.init_app(app)

    # Routes
    @app.route('/')
    def index():
        """ Default root route """
        return render_template('index.html', data="Some Arbitrary Data")

    # Catchall redirect route.
    @app.route('/<string:page_name>/')
    def render_static(page_name):
        """ Catch all for undefined routes. Return the requested static page. """
        if page_name == 'favicon.ico':
            return abort(404)
        return render_template('%s.html' % page_name)

    # Add an error handler. This is useful for debugging the live application,
    # however, you should disable the output of the exception for production
    # applications.
    @app.errorhandler(500)
    def server_error(e):
        print(e)
        return """
        An internal error occurred: <pre>{}</pre>
        See logs for full stacktrace.
        """.format(e), 500

    return app
