# import logging
from flask import Flask, render_template, abort, request, redirect, url_for  # , current_app
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

    @app.route('/user/<int:id>')
    def view(id):
        user = model_db.read(id)
        return render_template('view.html', user=user)

    @app.route('/user/add', methods=['GET', 'POST'])
    def add():
        if request.method == 'POST':
            data = request.form.to_dict(flat=True)  # TODO: Check for security. Possible refactor.
            data['admin'] = True if 'admin' in data.keys() and data['admin'] == 'on' else False
            user = model_db.create(data)
            return redirect(url_for('view', id=user['id']))
        return render_template('user_form.html', action='Add', user={})

    @app.route('/user/<int:id>/edit', methods=['GET', 'POST'])
    def edit(id):
        user = model_db.read(id)
        if request.method == 'POST':
            data = request.form.to_dict(flat=True)  # TODO: Check for security. Possible refactor.
            data['admin'] = True if 'admin' in data and data['admin'] == 'on' else False
            user = model_db.update(data, id)
            return redirect(url_for('view', id=user['id']))
        return render_template('user_form.html', action='Edit', user=user)


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
