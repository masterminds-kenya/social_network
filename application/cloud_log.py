import logging
from google.cloud import logging as google_logging
from google.cloud.logging.handlers import CloudLoggingHandler  # , setup_logging


class CloudLog(logging.getLoggerClass()):
    """Extended python Logger class that attaches a google cloud log handler. """
    DEFAULT_LOGGER_NAME = 'application'
    DEFAULT_LEVEL = logging.INFO
    DEFAULT_HANDLER_NAME = 'alert'

    def __init__(self, name=None, handler_name=None, level=None, log_client=None, rooted=True):
        name = self.make_logger_name(name)
        super().__init__(name)
        level = self.get_level(level)
        self.setLevel(level)
        handler = self.make_cloud_handler(handler_name, log_client)
        self.addHandler(handler)
        if rooted:
            self.parent = logging.root

    @classmethod
    def get_level(cls, level=None):
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

    @classmethod
    def make_logger_name(cls, parent_name=None):
        """Returns a lowercase name for a logger based on provided input or default value. """
        if not parent_name or not isinstance(parent_name, str):
            parent_name = getattr(cls, 'DEFAULT_LOGGER_NAME', 'root')
        if not parent_name:
            raise TypeError("Either a parent_name, or a default, string must be provided. ")
        return parent_name.lower()

    @classmethod
    def make_handler_name(cls, name=None):
        """Returns a lowercase name based on the given input or default value. """
        if not name or not isinstance(name, str):
            name = getattr(cls, 'DEFAULT_HANDLER_NAME', None)
        if not name:
            raise TypeError("Either a name, or a default name, string must be provided. ")
        return name.lower()

    @classmethod
    def make_cloud_handler(cls, handler_name=None, log_client=None, level=None):
        """Creates a handler for cloud logging with the provided name and optional level. """
        handler_name = cls.make_handler_name(handler_name)
        if not isinstance(log_client, google_logging.Client):
            log_client = google_logging.Client()
        handler = CloudLoggingHandler(log_client, name=handler_name)
        if level:
            handler.setLevel(level)
        return handler

    @staticmethod
    def make_base_logger(name=None, handler_name=None, level=None, log_client=None):
        """Used to create a logger with a cloud handler when a CloudLog instance is not desired. """
        name = CloudLog.make_logger_name(name)
        level = CloudLog.get_level(level)
        handler = CloudLog.make_cloud_handler(handler_name, log_client)
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
        return logger

    @staticmethod
    def test_loggers(app, logger_names=list(), loggers=list()):
        """Used for testing the log setups. """
        app_loggers = [(name, getattr(app, name)) for name in logger_names if hasattr(app, name)]
        logging.info(f"Expected {len(logger_names)} and found {len(app_loggers)} named loggers. ")
        if hasattr(app, 'logger'):
            app_loggers.insert(0, ('Default', app.logger))
        if loggers:
            logging.info(f"Investigating {len(loggers)} independent loggers. ")
            loggers = [('root', logging)] + app_loggers + [(num, ea) for num, ea in enumerate(loggers)]
        else:
            loggers = [('root', logging)] + app_loggers
        logging.info(f"Total loggers: {len(loggers)} ")
        logging.info("================ Warning messages for each Logger ==========================")
        for name, logger in loggers:
            if hasattr(logger, 'warning'):
                logger.warning(f"from logger - {name} ")
            else:
                logging.warning(f"No 'warning' method on logger {name} ")
