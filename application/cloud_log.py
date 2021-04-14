import logging
from google.cloud import logging as google_logging
# from google.cloud.logging.resource import Resource
from google.cloud.logging.handlers import CloudLoggingHandler, setup_logging


class CloudLog(logging.getLoggerClass()):
    """Use for Google Cloud Logging to gather context values and have the expected log level methods. """
    DEFAULT_LOGGER_NAME = 'application'
    DEFAULT_LEVEL = logging.INFO
    DEFAULT_HANDLER_NAME = 'ALERT'

    def __init__(self, name=None, handler_name=None, level=None):
        name = self.get_parent_name(name)
        super().__init__(name)
        level = self.get_level(level)
        name = self.get_handler_name(handler_name)
        # cloud_log = self.get_parent_logger(parent_name)
        self.setLevel(level)
        log_client = google_logging.Client()
        self.addHandler(CloudLoggingHandler(log_client, name=name))

    def get_level(self, level=None):
        """Returns the level value, based on the input string or integer if provided, or by using the default value. """
        if level is None:
            level = getattr(level, 'DEFAULT_LEVEL', logging.warn)
        name_to_level = logging._nameToLevel
        if isinstance(level, str):
            level = name_to_level.get(level.upper(), None)
            if level is None:
                raise ValueError("The level string was not a recognized value. ")
        elif isinstance(level, int):
            if level not in name_to_level.values():
                raise ValueError("The level integer was not a recognized value. ")
        else:
            raise TypeError("The level, or default level, must be an appropriate str or int value. ")
        return level

    def get_name(self, parent_name=None):
        """Returns a parent name for a logger based on provided input or default value. """
        if not parent_name or not isinstance(parent_name, str):
            parent_name = getattr(self, 'DEFAULT_PARENT_LOGGER_NAME', 'root')
        if not parent_name:
            raise TypeError("Either a parent_name, or a default, string must be provided. ")
        return parent_name

    def get_handler_name(self, name=None):
        """Returns an uppercase name based on the given input or default value. """
        if not name or not isinstance(name, str):
            name = getattr(self, 'DEFAULT_NAME', None)
        if not name:
            raise TypeError("Either a name, or a default name, string must be provided. ")
        return name.upper()


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


def test_log(app, g_log):
    """Used for testing the log setups. """
    logging.info('Root logging message. ')
    app.logger.info('App logging. ')
    if hasattr(g_log, 'info'):
        g_log.info('Constructed Logger Info. ')
    else:
        print(f"No 'info' method on g_log: {g_log} ")
    print("-------------------------------------------------")
    for attr in dir(g_log):
        print(f"{attr:<18} {getattr(g_log, attr)} ")
    print("-------------------------------------------------")
    # app.alert.info('Alert logging info. ')
