import logging
from flask import Flask  # , render_template, abort, request, flash, redirect, url_for  # , current_app
from . import model_db
# from os import environ

# DEPLOYED_URL = environ.get('DEPLOYED_URL')
# LOCAL_URL = 'http://127.0.0.1:8080'
# # URL, LOCAL_ENV = '', ''
# if environ.get('GAE_INSTANCE'):
#     URL = DEPLOYED_URL
#     LOCAL_ENV = False
# else:
#     environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
#     URL = LOCAL_URL
#     LOCAL_ENV = True


# class Result:
#     """ used for campaign results """
#     def __init__(self, media_type=None, metrics=set()):
#         self.media_type = media_type
#         self.posts = []
#         self.metrics = Result.lookup_metrics[self.media_type]

#     @staticmethod
#     def define_metrics():
#         rejected = {'insight', 'basic'}
#         added = {'comments_count', 'like_count'}
#         metrics = {k: v.extend(added) for k, v in model_db.Post.metrics.items() if k not in rejected}
#         return metrics

#     lookup_metrics = define_metrics()


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
