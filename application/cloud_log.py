import logging
from flask import json
from google.cloud import logging as cloud_logging
from google.cloud.logging.handlers import CloudLoggingHandler  # , setup_logging
from google.cloud.logging_v2.handlers.transports import BackgroundThreadTransport
from google.oauth2 import service_account
from google.cloud.logging import Resource
from os import environ
from datetime import datetime as dt

DEFAULT_FORMAT = logging.Formatter('%(levelname)s:%(name)s:%(message)s')


class LowPassFilter(logging.Filter):
    """Only allows LogRecords that are below the specified log level, according to levelno. """

    def __init__(self, name: str, level: int) -> None:
        super().__init__(name=name)
        self.below_level = level

    def filter(self, record):
        if record.name == self.name and record.levelno > self.below_level - 1:
            return False
        return True


class StreamClient:
    """Substitute for google.cloud.logging.Client, whose presence triggers standard library logging techniques. """

    def __init__(self, name, labels=None, resource=None, project=None, handler=None):
        if not project and isinstance(labels, dict):
            project = labels.get('project', labels.get('project_id', None))
        if not project:
            project = environ.get('GOOGLE_CLOUD_PROJECT', environ.get('PROJECT_ID', ''))
        self.project = project
        self.handler_name = name.lower()
        self.labels = labels if isinstance(labels, dict) else {'project': project}
        self.resource = resource
        self.handler = self.prepare_handler(handler)

    def prepare_handler(self, handler_param):
        """Creates or updates a logging.Handler with the correct name and attaches the labels and resource. """
        if isinstance(handler_param, type):
            handler = handler_param()  # handler_param is a logging.Handler class.
        elif issubclass(handler_param.__class__, logging.Handler):
            handler = handler_param  # handler_param is the handler instance we wanted.
        else:  # assume handler_param is None or a stream for logging.StreamHandler
            try:
                handler = logging.StreamHandler(handler_param)
            except Exception as e:
                logging.exception(e)
                raise ValueError("StreamClient handler must be a stream (like stdout) or a Handler class or instance. ")
        handler.set_name(self.handler_name)
        handler.labels = self.labels
        handler.resource = self.resource
        return handler

    def logger(self, name):
        """Similar interface of google.cloud.logging.Client, but returns standard library logging.Handler instance. """
        if isinstance(name, str):
            name = name.lower()
        if name != self.handler_name:
            return None
        return self.handler


class StreamTransport(BackgroundThreadTransport):
    """Allows CloudParamHandler to use StreamHandler methods when using StreamClient. """

    def __init__(self, client, name, *, grace_period=0, batch_size=0, max_latency=0):
        self.client = client
        self.handler = client.logger(name)
        self.grace_period = grace_period
        self.batch_size = batch_size
        self.max_latency = max_latency

    def create_entry(self, record, message, **kwargs):
        """Format entry close to (but not exact) the style of BackgroundThreadTransport Worker queue """
        entry = {
            "message": message,
            "python_logger": record.name,
            "severity": record.levelname,
            "timestamp": dt.utcfromtimestamp(record.created),
            }
        entry.update({key: val for key, val in kwargs.items() if val})
        return entry

    def send(self, record, message, **kwargs):
        """Similar to standard library logging.StreamHandler.emit, but with a json dict of appropriate values. """
        entry = self.create_entry(record, message, **kwargs)
        entry = json.dumps(entry)
        try:
            stream = self.stream
            stream.write(entry + self.terminator)  # std library logging issue 35046: merged two stream.writes into one.
            self.flush()
        except RecursionError:  # See standard library logging issue 36272
            raise
        except Exception:
            self.handleError(record)

    @property
    def stream(self):
        """Passes through the original Handler stream. """
        return self.handler.stream

    @property
    def terminator(self):
        """Passes through the original Handler terminator character(s). """
        if not getattr(self, '_terminator', None):
            self._terminator = self.handler.terminator
        return self._terminator

    def flush(self):
        self.handler.flush()

    def handleError(self, record):
        """Passes through the original Handler handleError method. """
        return self.handler.handleError(record)


class CloudParamHandler(CloudLoggingHandler):
    """Emits log by CloudLoggingHandler technique with a valid Client, or by StreamHandler if client is None. """

    filter_keys = ('_resource', '_trace', '_span_id', '_http_request', '_source_location', '_labels', '_trace_str',
                   '_span_id_str', '_http_request_str', '_source_location_str', '_labels_str', '_msg_str')

    def __init__(self, client, name='param_handler', resource=None, labels=None, stream=None, ignore=None):
        if client in (None, logging):
            client = StreamClient(name, labels, resource, handler=stream)
        transport = StreamTransport if isinstance(client, StreamClient) else BackgroundThreadTransport
        super().__init__(client, name=name, transport=transport, resource=resource, labels=labels, stream=stream)
        self.ignore = ignore  # self._data_keys = self.get_data_keys(ignore)

    def get_data_keys(self, ignore=None, ignore_str_keys=True):
        """DEPRECATED. Returns a list of the desired property names for logging that are set by CloudLoggingHandler. """
        keys = set(key[1:] for key in self.filter_keys if not (ignore_str_keys and key.endswith('_str')))
        ignore = self.ignore if ignore is None else ignore
        if isinstance(ignore, str):
            ignore = {ignore, }
        if isinstance(ignore, (list, tuple, set)):
            ignore = set(key.lstrip('_') for key in ignore)
        else:
            ignore = set()
        keys = keys.difference(ignore)
        return keys

    def prepare_record_data(self, record):
        """Update record attributes set by CloudLoggingHandler and move http_request to labels to assist in logging. """
        resource = getattr(record, '_resource', None)
        if self.resource and not resource:
            record._resource = resource = self.resource
        http_req = getattr(record, '_http_request', None)
        http_labels = {} if not http_req else {'_'.join(('http', key)): val for key, val in http_req.items()}
        handler_labels = getattr(self, 'labels', {})
        record_labels = getattr(record, '_labels', {})
        labels = {**http_labels, **handler_labels, **record_labels}
        record._labels = labels
        record._http_request = None
        if isinstance(self.client, StreamClient) and resource:
            record._resource = resource._to_dict()
        return record

    def emit(self, record):
        """After preparing the record data, will call the appropriate StreamTransport or BackgroundThreadTransport. """
        self.prepare_record_data(record)
        super().emit(record)


class CloudLog(logging.getLoggerClass()):
    """Extended python Logger class that attaches a google cloud log handler. """
    APP_LOGGER_NAME = 'application'
    APP_HANDLER_NAME = 'app'
    DEFAULT_LOGGER_NAME = None
    DEFAULT_HANDLER_NAME = None
    DEFAULT_LEVEL = logging.INFO
    DEFAULT_RESOURCE_TYPE = 'gae_app'  # 'logging_log', 'global', or any key from RESOURCE_REQUIRED_FIELDS
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
    RESERVED_KWARGS = ('stream', 'fmt', 'format', 'handler_name', 'handler_level', 'parent', 'res_type', 'cred_or_path')
    CLIENT_KW = ('project', 'credentials', 'client_info', 'client_options')  # also: '_http', '_use_grpc'

    def __init__(self, name=None, level=None, resource=None, client=None, **kwargs):
        stream = kwargs.pop('stream', None)
        fmt = kwargs.pop('fmt', kwargs.pop('format', DEFAULT_FORMAT))
        # 'handler_name' is ignored, using name for both the logger and handler
        handler_level = kwargs.pop('handler_level', None)
        parent = kwargs.pop('parent', logging.root)
        # 'res_type' is passed through to Resource constructor
        cred_or_path = kwargs.pop('cred_or_path', None)
        if client and cred_or_path:
            raise ValueError("Unsure how to prioritize the passed 'client' and 'cred_or_path' values. ")
        client = client or cred_or_path
        client_kwargs = {key: kwargs.pop(key) for key in ('client_info', 'client_options') if key in kwargs}
        name = self.normalize_logger_name(name)
        super().__init__(name)
        level = self.normalize_level(level)
        self.setLevel(level)
        if not isinstance(resource, Resource):  # resource may be None, a Config obj, or a dict.
            resource = self.make_resource(resource, **kwargs)
        self.resource = resource._to_dict()
        self.labels = getattr(resource, 'labels', self.get_environment_labels(environ))
        if client is logging:
            self.propagate = False
        else:    # client may be None, a cloud_logging.Client, a credential object or path.
            client = self.make_client(client, **client_kwargs, **self.labels)
        self.client = client  # accessing self.project may, on edge cases, set self.client
        # self._project = self.project  # may create and assign self.client if required to get project id.
        handler = self.make_handler(name, handler_level, resource, client, fmt=fmt, stream=stream, **self.labels)
        self.addHandler(handler)
        if parent == name:
            parent = None
        elif parent and isinstance(parent, str):
            parent = logging.getLogger(parent.lower())
        elif parent and not isinstance(parent, logging.getLoggerClass()):
            raise TypeError("The 'parent' value must be a string, None, or an existing logger. ")
        if parent:
            self.parent = parent

    @property
    def project(self):
        """If unknown, computes & sets from labels, resource, client, environ, or created client. May set client. """
        if not getattr(self, '_project', None):
            project = self.labels.get('project', None)
            if not project and self.resource:
                project = self.resource.get('labels', {})
                project = project.get('project_id') or project.get('project')
            if not project and isinstance(self.client, cloud_logging.Client):
                project = self.client.project
            if not project:
                project = environ.get('GOOGLE_CLOUD_PROJECT', environ.get('PROJECT_ID', None))
            if not project:
                cred_path = environ.get('GOOGLE_APPLICATION_CREDENTIALS', None)
                self.client = self.make_client(cred_path)
                project = self.client.project
            self._project = project
        return self._project

    @classmethod
    def normalize_level(cls, level=None):
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
    def normalize_logger_name(cls, name=None):
        """Returns a lowercase name for a logger based on provided input or default value. """
        if not name or not isinstance(name, str):
            name = cls.DEFAULT_LOGGER_NAME
        if not name:
            raise TypeError("Either a parent_name, or a default, string must be provided. ")
        return name.lower()

    @classmethod
    def normalize_handler_name(cls, name=None):
        """Returns a lowercase name based on the given input or default value. """
        if not name or not isinstance(name, str):
            name = cls.DEFAULT_HANDLER_NAME
        if not name:
            raise TypeError("Either a name, or a default name, string must be provided. ")
        return name.lower()

    @classmethod
    def make_client(cls, cred_or_path=None, **kwargs):
        """Creates the appropriate client, with appropriate handler for the environment, as used by other methods. """
        if isinstance(cred_or_path, cloud_logging.Client):
            return cred_or_path
        client_kwargs = {key: kwargs[key] for key in cls.CLIENT_KW if key in kwargs}  # such as 'project'
        if isinstance(cred_or_path, service_account.Credentials):
            credentials = cred_or_path
        elif cred_or_path:
            credentials = service_account.Credentials.from_service_account_file(cred_or_path)
            credentials = credentials.with_scopes(cls.LOG_SCOPES)
        else:
            credentials = None
        client_kwargs.setdefault('credentials', credentials)
        log_client = cloud_logging.Client(**client_kwargs)
        return log_client

    @classmethod
    def get_resource_fields(cls, settings):
        """For a given resource type, extract the expected required fields from the kwargs passed and project_id. """
        res_type = settings.pop('res_type', cls.DEFAULT_RESOURCE_TYPE)
        project_id = settings.get('project_id', settings.get('project', ''))
        if not project_id:
            project_id = environ.get('PROJECT_ID', environ.get('PROJECT', environ.get('GOOGLE_CLOUD_PROJECT', '')))
        pid = 'project_id'
        for key in cls.RESOURCE_REQUIRED_FIELDS[res_type]:
            backup_value = project_id if key == pid else ''
            if key not in settings and not backup_value:
                logging.warning(f"Could not find {key} for Resource {res_type}. ")
            settings.setdefault(key, backup_value)
        return res_type, settings

    @classmethod
    def get_environment_labels(cls, config=environ):
        """Returns a dict of context parameters, using either the config dict or values found in the environment. """
        return {
            'gae_env': config.get('GAE_ENV', ''),
            'project': config.get('GOOGLE_CLOUD_PROJECT', ''),
            'project_id': config.get('PROJECT_ID', ''),
            'service': config.get('GAE_SERVICE', ''),
            'module_id': config.get('GAE_SERVICE', ''),
            'code_service': config.get('CODE_SERVICE', ''),  # Either local or GAE_SERVICE value
            'version_id': config.get('GAE_VERSION', ''),
            'zone': config.get('PROJECT_ZONE', ''),
            }

    @classmethod
    def make_resource(cls, config, **kwargs):
        """Creates an appropriate resource to help with logging. The 'config' can be a dict or config.Config object. """
        if config and not isinstance(config, dict):
            config = getattr(config, '__dict__', None)
        if not config:
            config = environ
        added_labels = cls.get_environment_labels(config)
        for key, val in added_labels.items():
            kwargs.setdefault(key, val)
        res_type, labels = cls.get_resource_fields(kwargs)
        return Resource(res_type, labels)

    @classmethod
    def make_formatter(cls, fmt=DEFAULT_FORMAT, datefmt=None):
        """Creates a standard library formatter to attach to a handler. """
        if isinstance(fmt, logging.Formatter):
            return fmt
        return logging.Formatter(fmt, datefmt=datefmt)

    @classmethod
    def make_handler(cls, name=None, level=None, res=None, client=None, **kwargs):
        """Creates a cloud logging handler, or a standard library StreamHandler if log_client is logging. """
        stream = kwargs.pop('stream', None)
        fmt = kwargs.pop('fmt', kwargs.pop('format', DEFAULT_FORMAT))
        cred_or_path = kwargs.pop('cred_or_path', client)
        if not isinstance(res, Resource):  # res may be None, a Config obj, or a dict.
            res = cls.make_resource(res, **kwargs)
        labels = getattr(res, 'labels', None)
        if not labels:
            labels = cls.get_environment_labels()
            labels.update(kwargs)
        name = cls.normalize_handler_name(name)
        handler_kwargs = {'name': name, 'labels': labels}
        if res:
            handler_kwargs['resource'] = res
        if stream:
            handler_kwargs['stream'] = stream
        if client is not logging:
            client = cls.make_client(cred_or_path, **labels)  # cred_or_path is likely same as client.
        handler = CloudParamHandler(client, **handler_kwargs)  # CloudLoggingHandler if client, else StreamHandler.
        if level:
            level = cls.normalize_level(level)
            handler.setLevel(level)
        fmt = cls.make_formatter(fmt)
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
    def make_base_logger(cls, name=None, level=None, res=None, client=None, **kwargs):
        """Used to create a logger with a cloud handler when a CloudLog instance is not desired. """
        fmt = kwargs.pop('fmt', kwargs.pop('format', DEFAULT_FORMAT))
        handler_name = kwargs.pop('handler_hame', name)
        handler_level = kwargs.pop('handler_level', None)
        name = cls.normalize_logger_name(name)
        logger = logging.getLogger(name)
        handler = cls.make_handler(handler_name, handler_level, res, client, fmt=fmt, **kwargs)
        logger.addHandler(handler)
        level = cls.normalize_level(level)
        logger.setLevel(level)
        return logger

    @staticmethod
    def test_loggers(app, logger_names=list(), loggers=list(), levels=('warning', 'info', 'debug'), context=''):
        """Used for testing the log setups. """
        from pprint import pprint
        if not app.got_first_request:
            app.try_trigger_before_first_request_functions()
        if logger_names is not None and not logger_names:
            logger_names = app.log_list
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
        pprint("=================== App Log Client Credentials ===================")
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


def setup_cloud_logging(service_account_path, base_log_level, cloud_log_level, config=None, extra=None):
    """Function to setup logging with google.cloud.logging when not on Google Cloud App Standard. """
    log_client = CloudLog.make_client(service_account_path)
    log_client.get_default_handler()
    log_client.setup_logging(log_level=base_log_level)  # log_level sets the logger, not the handler.
    # TODO: Verify - Does any modifications to the default 'python' handler from setup_logging invalidate creds?
    root_handler = logging.root.handlers[0]
    low_filter = LowPassFilter(CloudLog.APP_LOGGER_NAME, cloud_log_level)
    root_handler.addFilter(low_filter)
    fmt = getattr(root_handler, 'formatter', None)
    if not fmt:
        fmt = DEFAULT_FORMAT
        root_handler.setFormatter(fmt)
    resource = CloudLog.make_resource(config)
    handler = CloudLog.make_handler(CloudLog.APP_HANDLER_NAME, cloud_log_level, resource, log_client, fmt=fmt)
    logging.root.addHandler(handler)
    if extra is None:
        extra = []
    elif isinstance(extra, str):
        extra = [extra]
    cloud_logs = [CloudLog(name, base_log_level, resource, log_client, fmt=fmt) for name in extra]
    return (log_client, *cloud_logs)
