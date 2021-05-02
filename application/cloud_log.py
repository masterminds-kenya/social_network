import logging
from google.cloud import logging as google_logging
from google.cloud import logging as cloud_logging
from google.cloud.logging.handlers import CloudLoggingHandler  # , setup_logging
from google.oauth2 import service_account


class CloudLog(logging.getLoggerClass()):
    """Extended python Logger class that attaches a google cloud log handler. """
    DEFAULT_LOGGER_NAME = 'application'
    DEFAULT_LEVEL = logging.INFO
    DEFAULT_HANDLER_NAME = 'alert'
    LOG_SCOPES = (
        'https://www.googleapis.com/auth/logging.read',
        'https://www.googleapis.com/auth/logging.write',
        'https://www.googleapis.com/auth/logging.admin',
        'https://www.googleapis.com/auth/cloud-platform',
        )

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
    def move_handlers(source, target, log_level=None):
        """Move all the google.cloud.logging handlers from source to target logger, applying log_level if provided. """
        if not all(isinstance(logger, logging.getLoggerClass()) for logger in (source, target)):
            raise ValueError('Both source and target must be loggers. ')
        stay, move = [], []
        for handler in source.handlers:
            if isinstance(handler, CloudLoggingHandler):
                if log_level:
                    handler.level = log_level
                move.append(handler)
            else:
                stay.append(handler)
        if not move:
            return
        target.handlers.extend(move)
        source.handlers = stay
        return

    @staticmethod
    def get_named_handler(logger=logging.root, name="python"):
        """Returns the CloudLoggingHandler with the matching name attached to the provided logger. """
        handlers = getattr(logger, 'handlers', [])
        for handle in handlers:
            if isinstance(handle, CloudLoggingHandler) and handle.name == name:
                return handle
        return None

    @staticmethod
    def make_base_logger(name=None, handler_name=None, level=None, log_client=None):
        """Used to create a logger with a cloud handler when a CloudLog instance is not desired. """
        name = CloudLog.make_logger_name(name)
        level = CloudLog.get_level(level)
        logger = logging.getLogger(name)
        if handler_name:
            handler = CloudLog.make_cloud_handler(handler_name, log_client)
            logger.addHandler(handler)
        logger.setLevel(level)
        return logger

    @staticmethod
    def test_loggers(app, logger_names=list(), loggers=list(), levels=('warning', 'info', 'debug'), context=''):
        """Used for testing the log setups. """
        app_loggers = [(name, getattr(app, name)) for name in logger_names if hasattr(app, name)]
        print(f"Expected {len(logger_names)} and found {len(app_loggers)} named loggers. ")
        if hasattr(app, 'logger'):
            app_loggers.insert(0, ('Default', app.logger))
        if loggers:
            print(f"Investigating {len(loggers)} independent loggers. ")
            loggers = [('root', logging)] + app_loggers + [(num, ea) for num, ea in enumerate(loggers)]
        else:
            loggers = [('root', logging)] + app_loggers
        print(f"Total loggers: {len(loggers)} ")
        code = app.config.get('CODE_ENVIRONMENT', 'UNKNOWN')
        print("--------------- Logger Tests --------------")
        for name, logger in loggers:
            for level in levels:
                if hasattr(logger, level):
                    getattr(logger, level)(' - '.join((context, name, level, code)))
                else:
                    logging.warning(f"{context} in {code}: No {level} method on logger {name} ")


def setup_cloud_logging(config, base_log_level, cloud_log_level, extra=None):
    """Function to setup logging with google.cloud.logging when not on Google Cloud App Standard. """
    service_account_path = getattr(config, 'GOOGLE_APPLICATION_CREDENTIALS', None)
    creds = service_account.Credentials.from_service_account_file(service_account_path)
    creds = creds.with_scopes(CloudLog.LOG_SCOPES)
    log_client = cloud_logging.Client(credentials=creds)
    log_client.setup_logging(log_level=base_log_level)  # log_level sets the logger, not the handler.
    # Note: any modifications to the default 'python' handler from setup_logging will invalidate creds.
    # cloud_handler = CloudLog.get_named_handler()
    handler = CloudLog.make_cloud_handler('app', log_client, cloud_log_level)
    logging.root.addHandler(handler)
    if extra is None:
        extra = []
    elif isinstance(extra, str):
        extra = [extra]
    cloud_logs = [CloudLog(ea, ea, base_log_level, log_client) for ea in extra]
    return (log_client, *cloud_logs)
