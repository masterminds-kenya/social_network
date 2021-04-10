import logging
from google.cloud import logging as google_logging
# from google.cloud.logging.resource import Resource
from google.cloud.logging.handlers import CloudLoggingHandler, setup_logging


def log_setup(log_type, log_level=logging.WARN):
    """Allows for various techniques to setup the logging for the app and environment. """
    # Configure logging depth: ?NOTSET?, DEBUG, INFO, WARNING, ERROR, CRITICAL
    # logging.basicConfig(level=log_level)
    log_type = log_type.upper()
    log_client = google_logging.Client()
    if log_type == 'ALL':
        log_name = 'LOG'
        handler = CloudLoggingHandler(log_client, name=log_name)
        g_log = logging.getLogger('cloudLogger')
        g_log.setLevel(log_level)
        g_log.addHandler(handler)
        # logging.getLogger().setlevel(log_level)
        # setup_logging(handler)
        # app.alert = app.logger
    elif log_type == 'ROOT':
        handler = CloudLoggingHandler(log_client)
        logging.getLogger().setLevel(log_level)
        setup_logging(handler)
        g_log = logging.getLogger()
    elif log_type == 'BASIC':
        logging.basicConfig(level=log_level)
        g_log = logging.getLogger()
    else:
        log_name = log_type
        # handler = CloudLoggingHandler(log_client, name=log_name)
        g_log = log_client.logger(log_name)
        g_log.setLevel(log_level)
        # g_log.addHandler(handler)
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
    return g_log
