import logging
from google.cloud import logging as cloud_logging
from google.cloud.logging.handlers import CloudLoggingHandler  # , setup_logging
from google.oauth2 import service_account
from google.cloud.logging import Resource


class CloudLog(logging.getLoggerClass()):
    """Extended python Logger class that attaches a google cloud log handler. """
    APP_LOGGER_NAME = 'application'
    APP_HANDLER_NAME = 'app'
    DEFAULT_LOGGER_NAME = None
    DEFAULT_HANDLER_NAME = None
    DEFAULT_LEVEL = logging.INFO
    DEFAULT_FORMAT = '%(levelname)s:%(name)s:%(message)s'
    LOG_SCOPES = (
        'https://www.googleapis.com/auth/logging.read',
        'https://www.googleapis.com/auth/logging.write',
        'https://www.googleapis.com/auth/logging.admin',
        'https://www.googleapis.com/auth/cloud-platform',
        )

    def __init__(self, name=None, handler_name=None, level=None, log_client=None, parent='root'):
        name = self.make_logger_name(name)
        super().__init__(name)
        level = self.get_level(level)
        self.setLevel(level)
        handler = self.make_handler(handler_name, log_client)
        self.addHandler(handler)
        if parent == name:
            parent = None
        elif parent == 'root':
            parent = logging.root
        elif parent and isinstance(parent, str):
            parent = logging.getLogger(parent.lower())
        elif parent and not isinstance(parent, logging.getLoggerClass()):
            raise TypeError("The 'parent' value must be a string, None, or an existing logger. ")
        if parent:
            self.parent = parent

    @classmethod
    def get_level(cls, level=None):
        """Returns the level value, based on the input string or integer if provided, or by using the default value. """
        if level is None:
            level = getattr(level, 'DEFAULT_LEVEL', logging.WARNING)
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
    def make_logger_name(cls, name=None):
        """Returns a lowercase name for a logger based on provided input or default value. """
        if not name or not isinstance(name, str):
            name = cls.DEFAULT_LOGGER_NAME
        if not name:
            raise TypeError("Either a parent_name, or a default, string must be provided. ")
        return name.lower()

    @classmethod
    def make_handler_name(cls, name=None):
        """Returns a lowercase name based on the given input or default value. """
        if not name or not isinstance(name, str):
            name = cls.DEFAULT_HANDLER_NAME
        if not name:
            raise TypeError("Either a name, or a default name, string must be provided. ")
        return name.lower()

    @classmethod
    def make_client(cls, credential_path=None, credentials=None):
        """Creates the appropriate client, with appropriate handler for the environment, as used by other methods. """
        if credential_path:
            credentials = service_account.Credentials.from_service_account_file(credential_path)
            credentials = credentials.with_scopes(cls.LOG_SCOPES)
        kwargs = {'credentials': credentials} if credentials else {}
        log_client = cloud_logging.Client(**kwargs)
        return log_client

    @classmethod
    def make_resource(cls, config, **kwargs):
        """Creates an appropriate resource to help with logging. """
        # labels = {'project_id': config.get('PROJECT_ID'), 'zone': config.get('PROJECT_ZONE')}
        labels = {'project_id': getattr(config, 'PROJECT_ID', None), 'zone': getattr(config, 'PROJECT_ZONE', None)}
        # if config.get('GAE_ENV'):
        #     labels['module_id'] = config.get('GAE_SERVICE')
        if getattr(config, 'GAE_ENV', None):
            labels['module_id'] = getattr(config, 'GAE_SERVICE', None)
        labels.update(kwargs)
        ty = 'global'  # 'logging_log', 'pubsub_subscription', 'pubsub_topic', 'reported_errors'
        return Resource(type=ty, labels=labels)

    @classmethod
    def make_formatter(cls, fmt=DEFAULT_FORMAT, datefmt=None):
        """Creates a standard library formatter to attach to a handler. """
        return logging.Formatter(fmt, datefmt=datefmt)

    @classmethod
    def make_handler(cls, handler_name=None, log_client=None, level=None, res=None, fmt=DEFAULT_FORMAT, cloud=True):
        """Creates a cloud logging handler, or a standard library StreamHandler if log_client is logging. """
        handler_name = cls.make_handler_name(handler_name)
        if not cloud:
            log_client = logging
        if log_client is not logging:
            if not isinstance(log_client, cloud_logging.Client):
                log_client = cls.make_client()
            handler_kwargs = {}
            if handler_name:
                handler_kwargs['name'] = handler_name
            if res and not isinstance(res, Resource):
                res = cls.make_resource(res)
            if res:
                handler_kwargs['resource'] = res
            handler = CloudLoggingHandler(log_client, **handler_kwargs)
        else:
            handler = logging.StreamHandler()
            if handler_name:
                handler.set_name(handler_name)
        if level:
            level = cls.get_level(level)
            handler.setLevel(level)
        if fmt and not isinstance(fmt, logging.Formatter):
            fmt = cls.make_formatter(fmt)
        if fmt:
            handler.setFormatter(fmt)
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
        if move:
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

    @classmethod
    def make_base_logger(cls, name=None, handler_name=None, level=None, log_client=None, res=None):
        """Used to create a logger with an optional cloud handler when a CloudLog instance is not desired. """
        name = cls.make_logger_name(name)
        logger = logging.getLogger(name)
        if handler_name:
            handler = cls.make_handler(handler_name, log_client, res=res)
            logger.addHandler(handler)
        level = cls.get_level(level)
        logger.setLevel(level)
        return logger

    @staticmethod
    def test_loggers(app, logger_names=list(), loggers=list(), levels=('warning', 'info', 'debug'), context=''):
        """Used for testing the log setups. """
        from pprint import pprint
        app_loggers = [(name, getattr(app, name)) for name in logger_names if hasattr(app, name)]
        print(f"Expected {len(logger_names)} and found {len(app_loggers)} named loggers. ")
        if hasattr(app, 'logger'):
            app_loggers.insert(0, ('App_Logger', app.logger))
        if loggers:
            print(f"Investigating {len(loggers)} independent loggers. ")
        loggers = [('root', logging.root)] + app_loggers + [(num, ea) for num, ea in enumerate(loggers)]
        print(f"Total loggers: {len(loggers)} ")
        code = app.config.get('CODE_ENVIRONMENT', 'UNKNOWN')
        print("=================== Logger Tests & Info ===================")
        log_count_str = ''
        all_handlers = []
        for name, logger in loggers:
            handlers = getattr(logger, 'handlers', 'not found')
            if isinstance(handlers, list):
                all_handlers.extend(handlers)
            log_count_str += f"{name} handlers: {str(handlers)} " + '\n'
            for level in levels:
                if hasattr(logger, level):
                    getattr(logger, level)(' - '.join((context, name, level, code)))
                else:
                    logging.warning(f"{context} in {code}: No {level} method on logger {name} ")
            print(f"--------------- {name} Logger Settings ------------------")
            pprint(logger.__dict__)
            print('-------------------------------------------------------------')
        print(f"=================== Details for each of {len(all_handlers)} handlers ===================")
        creds_list = []
        resources = []
        for handle in all_handlers:
            pprint(handle.__dict__)
            temp_client = getattr(handle, 'client', object)
            temp_creds = getattr(temp_client, '_credentials', None)
            if temp_creds:
                creds_list.append(temp_creds)
            resources.append(getattr(handle, 'resource', None))
            print("-------------------------------------------------")
        print("====================== Resources found attached to the Handlers ======================")
        if hasattr(app, '_resource_test'):
            resources.append(app._resource_test)
        for res in resources:
            if hasattr(res, '_to_dict'):
                pprint(res._to_dict())
            else:
                pprint(f"Resource was: {res} ")
        pprint("=================== App Log Client Credentials ===================")
        print(f"Currently have {len(creds_list)} creds from logger clients. ")
        creds_list = [(f"client_cred_{num}", ea) for num, ea in enumerate(set(creds_list))]
        print(f"With {len(creds_list)} unique client credentials. " + '\n')
        if hasattr(app, '_creds'):
            print("Adding _creds. ")
            creds_list.append(('_creds', app._creds))
        log_client = getattr(app, 'log_client', None)
        if log_client and log_client is not logging:
            print("Adding App Log Client Creds. ")
            creds_list.append(('App Log Client Creds', log_client._credentials))
        for name, creds in creds_list:
            pprint(f"{name}: {creds} ")
            pprint(creds.expired)
            pprint(creds.valid)
            pprint(creds.__dict__)
            pprint("--------------------------------------------------")
        if not creds_list:
            print("No credentials found to report.")


def setup_cloud_logging(service_account_path, base_log_level, cloud_log_level, extra=None):
    """Function to setup logging with google.cloud.logging when not on Google Cloud App Standard. """
    log_client = CloudLog.make_client(service_account_path)
    log_client.get_default_handler()
    log_client.setup_logging(log_level=base_log_level)  # log_level sets the logger, not the handler.
    # Note: any modifications to the default 'python' handler from setup_logging will invalidate creds.
    handler = CloudLog.make_handler(CloudLog.APP_HANDLER_NAME, log_client, cloud_log_level)
    logging.root.addHandler(handler)
    if extra is None:
        extra = []
    elif isinstance(extra, str):
        extra = [extra]
    cloud_logs = [CloudLog(name, name, base_log_level, log_client) for name in extra]
    return (log_client, *cloud_logs)
