import logging
from sys import stderr, stdout
from flask import json
from google.cloud import logging as cloud_logging
from google.cloud.logging.handlers import CloudLoggingHandler  # , setup_logging
from google.auth import default as creds_id
from google.oauth2 import service_account
from google.cloud.logging import Resource
from os import environ
# from googleapiclient.discovery import build


class LowPassFilter(logging.Filter):
    """Only allows LogRecords that are below the specified log level, according to levelno. """

    def __init__(self, name: str, level: int) -> None:
        super().__init__(name=name)
        self.below_level = level

    def filter(self, record):
        if record.name == self.name and record.levelno > self.below_level - 1:
            return False
        return True


class StructHandler(logging.StreamHandler):
    """EXPERIMENTAL. Will log a json with added parameters of where the log message came from. """
    DEFAULT_FORMAT = '%(levelname)s:%(name)s:%(message)s'

    def __init__(self, name, level=0, fmt=DEFAULT_FORMAT, stream=None, res=None, **kwargs):
        super().__init__(stream=stream)
        if name:
            self.set_name(name)
        if level:
            self.setLevel(level)
        if fmt and not isinstance(fmt, logging.Formatter):
            fmt = logging.Formatter(fmt)
        if fmt:
            self.setFormatter(fmt)
        if res and not isinstance(res, Resource):
            res = CloudLog.make_resource(res)
        if isinstance(res, Resource):
            self.resource = res
        self.project = environ.get('GOOGLE_CLOUD_PROJECT', environ.get('PROJECT_ID', ''))
        self.logName = 'projects/' + self.project + '/logs/' + self.name
        self.settings = self.get_settings(**kwargs)

    def get_settings(self, **kwargs):
        """Creates a dict with expected context settings and any passed kwargs. """
        rv = {
            'gae_env': environ.get('GAE_ENV', ''),
            'project': self.project,
            'service': environ.get('GAE_SERVICE', ''),
            'source': self._name,
            'region': environ.get('PROJECT_REGION', ''),
            'zone': environ.get('PROJECT_ZONE', ''),
        }
        rv.update(kwargs)
        return rv

    def get_log_path(self, record_name):
        """Computes the logName path for GCP. """
        path = 'projects/' + self.project + '/logs/' + record_name
        return path

    def format(self, record, alt=True):
        message = super().format(record)
        if alt:
            settings = self.settings.copy()
            settings['logName'] = self.get_log_path(record.name)
            settings['severity'] = record.levelname
            settings['message'] = message
            resource = getattr(self, 'resource', None)
            if resource:
                settings['resource'] = resource
            message = json.dumps(settings)
        return message


class CloudHandler(logging.StreamHandler):
    """EXPERIMENTAL. A handler that both uses the Google Logging API and writes to the standard outpout. """
    DEFAULT_FORMAT = '%(levelname)s:%(name)s:%(message)s'

    def __init__(self, name='', client=None, level=0, fmt=DEFAULT_FORMAT, resource=None):
        super().__init__()
        if name:
            self.set_name(name)
        if level:
            self.setLevel(level)
        if fmt and not isinstance(fmt, logging.Formatter):
            fmt = CloudLog.make_formatter(fmt)
        if fmt:
            self.setFormatter(fmt)
        if client is logging or not isinstance(client, cloud_logging.Client):
            client = None
        # if not isinstance(client, cloud_logging.Client):  # Either None, or assume a credential filepath.
        #     client = CloudLog.make_client(client)
        if not client:
            creds, project_id = creds_id(CloudLog.LOG_SCOPES)
            kwargs = {'credentials': creds} if creds else {}
            client = cloud_logging.Client(**kwargs)
        else:
            project_id = client.project
        if isinstance(resource, Resource):
            self.resource = resource
        self.gae_service = environ.get('GAE_SERVICE', '')
        self.client = client
        self.project_id = project_id

    def emit(self, record):
        message = self.format(record)
        print("This is the print: " + message)
        g_log = self.client.logger(self.name or record.name)

        info = {
            'severity_number': record.levelno,
            'severity_name': record.levelname,
            'python_logger': record.name,
            'service': self.gae_service,
            'project': self.project_id,
            'message': message,
        }
        # api_body = {
        #     'entries': [
        #         {
        #             'severity': record.levelno,
        #             'jsonPayload': {
        #                 'module': record.module,
        #                 'message': record.getMessage()
        #             },
        #             'logName': 'projects/' + self.project_id + '/logs/' + record.name,
        #             'resource': {
        #                 'type': 'global',
        #             }
        #         }
        #     ]
        # }
        # api_log(body=api_body).execute()
        kwargs = {'severity': record.levelno}
        res = getattr(self, 'resource', None)
        if res:
            kwargs['resource'] = res
        g_log.log_struct(info, **kwargs)


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
    RESOURCE_REQUIRED_FIELDS = {  # https://cloud.google.com/logging/docs/api/v2/resource-list
        'cloud_tasks_queue': ['project_id', 'queue_id', 'target_type', 'location'],
        'cloudsql_database': ['project_id', 'database_id', 'region'],
        'container': ['project_id', 'cluster_name', 'namespace_id', 'instance_id', 'pod_id', 'container_name', 'zone'],
        # 'k8s_container': RESOURCE_REQUIRED_FIELDS['container']
        'dataflow_step': ['project_id', 'job_id', 'step_id', 'job_name', 'region'],
        'dataproc_cluster': ['project_id', 'cluster_id', 'zone'],
        'datastore_database': ['project_id', 'database_id'],
        'datastore_index': ['project_id', 'database_id', 'index_id'],
        'deployment': ['project_id', 'name'],
        'folder': ['folder_id'],
        'gae_app': ['project_id', 'module_id', 'version_id', 'zone'],
        'gce_backend_service': ['project_id', 'backend_service_id', 'location'],
        'gce_instance': ['project_id', 'instance_id', 'zone'],
        'gce_project': ['project_id'],
        'gcs_bucket': ['project_id', 'bucket_name', 'location'],
        'generic_node': ['project_id', 'location', 'namespace', 'node_id'],
        'generic_task': ['project_id', 'location', 'namespace', 'job', 'task_id'],
        'global': ['project_id'],
        'logging_log': ['project_id', 'name'],
        'logging_sink': ['project_id', 'name', 'destination'],
        'project': ['project_id'],
        'pubsub_subscription': ['project_id', 'subscription_id'],
        'pubsub_topic': ['project_id', 'topic_id'],
        'reported_errors': ['project_id'],
    }

    def __init__(self, name=None, handler_name=None, log_client=None, level=None, fmt=DEFAULT_FORMAT, parent='root'):
        name = self.make_logger_name(name)
        super().__init__(name)
        level = self.get_level(level)
        self.setLevel(level)
        handler = self.make_handler(handler_name, log_client, None, fmt)
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
    def make_client(cls, cred_or_path):
        """Creates the appropriate client, with appropriate handler for the environment, as used by other methods. """
        if isinstance(cred_or_path, service_account.Credentials):
            credentials = cred_or_path
        elif cred_or_path:
            credentials = service_account.Credentials.from_service_account_file(cred_or_path)
            credentials = credentials.with_scopes(cls.LOG_SCOPES)
        else:
            credentials = None
        kwargs = {'credentials': credentials} if credentials else {}
        log_client = cloud_logging.Client(**kwargs)
        return log_client

    @classmethod
    def get_resource_fields(cls, project_id, settings):
        """For a given resource type, extract the expected required fields from the kwargs passed and project_id. """
        default_type = 'gae_app'  # 'global', 'logging_log', 'pubsub_subscription', 'pubsub_topic', 'reported_errors'
        res_type = settings.pop('res_type', default_type)
        pid = 'project_id'
        for key in cls.RESOURCE_REQUIRED_FIELDS[res_type]:
            backup_value = project_id if key == pid else None
            if key not in settings and not backup_value:
                logging.warning(f"Could not find {key} for Resource {res_type}. ")
            settings.setdefault(key, backup_value)
        return res_type, settings

    @classmethod
    def make_resource(cls, config, **kwargs):
        """Creates an appropriate resource to help with logging. The 'config' can be a dict or config.Config object. """
        if config and not isinstance(config, dict):
            config = getattr(config, '__dict__', None)
        if not config:
            raise TypeError("The 'config' must be a dict or an object with needed values in __dict__. ")
        project_id = config.get('PROJECT_ID')
        added_labels = {
            'gae_env': config.get('GAE_ENV'),
            'project_id': project_id,
            'code_service': config.get('CODE_SERVICE'),  # Either local or GAE_SERVICE
            'service': config.get('GAE_SERVICE'),
            'zone': config.get('PROJECT_ZONE')
            }
        for key, val in added_labels.items():
            kwargs.setdefault(key, val)
        res_type, labels = cls.get_resource_fields(project_id, kwargs)
        return Resource(res_type, labels)

    @classmethod
    def make_formatter(cls, fmt=DEFAULT_FORMAT, datefmt=None):
        """Creates a standard library formatter to attach to a handler. """
        return logging.Formatter(fmt, datefmt=datefmt)

    @classmethod
    def make_handler(cls, handler_name=None, log_client=None, level=None, fmt=DEFAULT_FORMAT, res=None):
        """Creates a cloud logging handler, or a standard library StreamHandler if log_client is logging. """
        handler_name = cls.make_handler_name(handler_name)
        if log_client is not logging:
            if not isinstance(log_client, cloud_logging.Client):
                log_client = cls.make_client()
            handler_kwargs = {}
            if handler_name:
                handler_kwargs['name'] = handler_name
            if res:
                if not isinstance(res, Resource):
                    res = cls.make_resource(res)
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
    def make_base_logger(cls, name=None, handler_name=None, log_client=None, level=None, fmt=DEFAULT_FORMAT, res=None):
        """Used to create a logger with an optional cloud handler when a CloudLog instance is not desired. """
        name = cls.make_logger_name(name)
        logger = logging.getLogger(name)
        if handler_name:
            handler = cls.make_handler(handler_name, log_client, None, fmt, res)
            logger.addHandler(handler)
        level = cls.get_level(level)
        logger.setLevel(level)
        return logger

    @staticmethod
    def test_loggers(app, logger_names=list(), loggers=list(), levels=('warning', 'info', 'debug'), context=''):
        """Used for testing the log setups. """
        from pprint import pprint
        app_loggers = [(name, getattr(app, name)) for name in logger_names if hasattr(app, name)]
        print(f"Found {len(app_loggers)} named attachments. ")
        app_loggers = [ea for ea in app_loggers if ea[1] is not None]
        print(f"Expected {len(logger_names)} and found {len(app_loggers)} named loggers. ")
        if hasattr(app, 'logger'):
            app_loggers.insert(0, ('App_Logger', app.logger))
        if loggers:
            print(f"Investigating {len(loggers)} independent loggers. ")
        loggers = [('root', logging.root)] + app_loggers + [(num, ea) for num, ea in enumerate(loggers)]
        print(f"Total loggers: {len(loggers)} ")
        code = app.config.get('CODE_SERVICE', 'UNKNOWN')
        print("=================== Logger Tests & Info ===================")
        found_handler_str = ''
        all_handlers = []
        for name, logger in loggers:
            adapter = None
            if isinstance(logger, logging.LoggerAdapter):
                adapter, logger = logger, logger.logger
            handlers = getattr(logger, 'handlers', ['not found'])
            if isinstance(handlers, list):
                all_handlers.extend(handlers)
            found_handler_str += f"{name} handlers: {', '.join([str(ea) for ea in handlers])} " + '\n'
            if adapter:
                print(f"-------------------------- {name} ADAPTER Settings --------------------------")
                pprint(adapter.__dict__)
            print(f"---------------------------- {name} Logger Settings ----------------------------")
            pprint(logger.__dict__)
            print(f'------------------------- Logger Calls: {name} -------------------------')
            for level in levels:
                if hasattr(adapter or logger, level):
                    getattr(adapter or logger, level)(' - '.join((context, name, level, code)))
                else:
                    logging.warning(f"{context} in {code}: No {level} method on logger {name} ")
        print(f"=================== Handler Info: found {len(all_handlers)} on tested loggers ===================")
        print(found_handler_str)
        creds_list = []
        resources = []
        for num, handle in enumerate(all_handlers):
            print(f"------------------------- {num}: {handle.name} -------------------------")
            pprint(handle.__dict__)
            temp_client = getattr(handle, 'client', object)
            temp_creds = getattr(temp_client, '_credentials', None)
            if temp_creds:
                creds_list.append(temp_creds)
            resources.append(getattr(handle, 'resource', None))
        print("=================== Resources found attached to the Handlers ===================")
        if hasattr(app, '_resource_test'):
            resources.append(app._resource_test)
        for res in resources:
            if hasattr(res, '_to_dict'):
                pprint(res._to_dict())
            else:
                pprint(f"Resource was: {res} ")
        pprint("\n=================== App Log Client Credentials ===================")
        log_client = getattr(app, 'log_client', None)
        if log_client is logging:
            log_client = None
        app_creds = log_client._credentials if log_client else None
        if app_creds in creds_list:
            app_creds = None
        print(f"Currently have {len(creds_list)} creds from logger clients. ")
        creds_list = [(f"client_cred_{num}", ea) for num, ea in enumerate(set(creds_list))]
        print(f"With {len(creds_list)} unique client credentials. " + '\n')
        if log_client and not app_creds:
            print("App Log Client Creds - already included in logger clients. ")
        elif app_creds:
            print("Adding App Log Client Creds. ")
            creds_list.append(('App Log Client Creds', app_creds))
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
    root_handler = logging.root.handlers[0]
    low_filter = LowPassFilter(CloudLog.APP_LOGGER_NAME, cloud_log_level)
    root_handler.addFilter(low_filter)
    fmt = getattr(root_handler, 'formatter', None) or CloudLog.DEFAULT_FORMAT
    handler = CloudLog.make_handler(CloudLog.APP_HANDLER_NAME, log_client, cloud_log_level, fmt)
    logging.root.addHandler(handler)
    if extra is None:
        extra = []
    elif isinstance(extra, str):
        extra = [extra]
    cloud_logs = [CloudLog(name, name, log_client, base_log_level, fmt) for name in extra]
    return (log_client, *cloud_logs)
