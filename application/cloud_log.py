import logging
from google.cloud import logging as google_logging
from google.cloud.logging.handlers import CloudLoggingHandler


class CloudLog(logging.getLoggerClass()):
    """Extended python Logger class that attaches a google cloud log handler. """
    DEFAULT_LOGGER_NAME = 'application'
    DEFAULT_LEVEL = logging.INFO
    DEFAULT_HANDLER_NAME = 'ALERT'

    def __init__(self, name=None, handler_name=None, level=None, log_client=None):
        name = self.get_name(name)
        super().__init__(name)
        level = self.get_level(level)
        handler_name = self.get_handler_name(handler_name)
        self.setLevel(level)
        if not isinstance(log_client, google_logging.Client):
            log_client = google_logging.Client()
        self.addHandler(CloudLoggingHandler(log_client, name=handler_name))

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
        """Returns name for a logging.Logger based on provided input or default value. """
        if not parent_name or not isinstance(parent_name, str):
            parent_name = getattr(self, 'DEFAULT_LOGGER_NAME', 'root')
        if not parent_name:
            raise TypeError("Either a parent_name, or a default, string must be provided. ")
        return parent_name

    def get_handler_name(self, name=None):
        """Returns an uppercase name based on the given input or default value. """
        if not name or not isinstance(name, str):
            name = getattr(self, 'DEFAULT_HANDLER_NAME', None)
        if not name:
            raise TypeError("Either a name, or a default name, string must be provided. ")
        return name.upper()


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
