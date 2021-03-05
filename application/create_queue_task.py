from flask import current_app as app
from flask.helpers import url_for
from google.api_core.exceptions import RetryError, AlreadyExists, GoogleAPICallError
from google.cloud import tasks_v2
# from google.cloud.tasks_v2.types.queue import Queue, RateLimits, RetryConfig, StackdriverLoggingConfig
# from google.cloud.tasks_v2.types import target
from google.protobuf import timestamp_pb2, duration_pb2
from datetime import timedelta, datetime as dt
from .model_db import Post
from os import environ
import json

PROJECT_ID = app.config.get('PROJECT_ID')
PROJECT_REGION = app.config.get('PROJECT_REGION')  # Google Docs said PROJECT_ZONE, but confirmed PROJECT_REGION works
CURRENT_SERVICE = app.config.get('CURRENT_SERVICE')
CAPTURE_SERVICE = app.config.get('CAPTURE_SERVICE', CURRENT_SERVICE)
COLLECT_SERVICE = app.config.get('COLLECT_SERVICE', CURRENT_SERVICE)
CAPTURE_QUEUE = app.config.get('CAPTURE_QUEUE', 'capture')
COLLECT_QUEUE = app.config.get('COLLECT_QUEUE', 'collect')
BETWEEN_COLLECT = 4  # Multiple collect-tasks starting time seperated by this number of seconds.
CAPTURE_IMAGE_QUEUE_NAMES = ('test-on-db-b', 'post', 'test')
COLLECT_PROCESS_ALLOWED = {'basic', 'metrics', 'data'}
client = tasks_v2.CloudTasksClient()


def try_task(parent, task):
    """Given the parent queue path and a constructed task dict, create/assign the task or log the error response. """
    try:
        response = client.create_task(parent=parent, task=task)
    except ValueError as e:
        app.logger.info(f"Invalid parameters for creating a task: \n {task}")
        app.logger.error(e)
        response = None
    except RetryError as e:
        app.logger.info(f"Retry Attempts exhausted for a task: \n {task}")
        app.logger.error(e)
        response = None
    except GoogleAPICallError as e:
        app.logger.info(f"Google API Call Error on creating a task: \n {task}")
        app.logger.error(e)
        response = None
    if response is not None:
        app.logger.info(f"Created task: {response} ")
    return response  # .name if response else None


def get_queue_path(process):
    """Creates or gets a queue for either the Capture API or the collect process. """
    override_service = None
    if not process:
        process = 'test'
    if process in CAPTURE_IMAGE_QUEUE_NAMES:
        is_capture = True
        service = CAPTURE_SERVICE
        override_service = service
        queue_type = CAPTURE_QUEUE
    elif process in COLLECT_PROCESS_ALLOWED:
        is_capture = False
        service = CURRENT_SERVICE
        if service != COLLECT_SERVICE:
            override_service = service
        queue_type = COLLECT_QUEUE
    else:
        is_capture, service, queue_type = False, None, None
        raise ValueError("The process must be one of CAPTURE_IMAGE_QUEUE_NAMES or COLLECT_PROCESS_ALLOWED. ")
    short_queue_name = f"{queue_type}-{service}-{process}".lower()
    full_queue_name = client.queue_path(PROJECT_ID, PROJECT_REGION, short_queue_name)
    try:
        q = client.get_queue(name=full_queue_name)
        app.logger.info(f"===== FOUND QUEUE: {q} =====")
        app.logger.info(dir(q))
        app.logger.info("-----------------------------")
    except Exception as e:
        app.logger.info(f"The {full_queue_name} queue does not exist, or could not be found. Attempting to create it. ")
        app.logger.info(e)
        q = None
    if q:
        # TODO: Check for critical parameters, update if needed.
        return full_queue_name
    rate_limits = {'max_concurrent_dispatches': 2 if is_capture else 1, 'max_dispatches_per_second': 500}
    queue_settings = {'name': full_queue_name, 'rate_limits': rate_limits}
    if override_service:
        queue_settings['app_engine_routing_override'] = {'service': override_service}
    min_backoff, max_backoff, max_life = duration_pb2.Duration(), duration_pb2.Duration(), duration_pb2.Duration()
    min_backoff.FromJsonString('10s' if is_capture else '7s')
    max_backoff.FromJsonString('3900s')  # 65 minutes, shortens last 1 of collect, last 2 of capture.
    max_life.FromJsonString('86100s')    # 5 minutes shy of 24 hours; shortens last of max_attempts?
    retry_config = {'max_attempts': 32, 'min_backoff': min_backoff, 'max_backoff': max_backoff, 'max_doublings': 10}
    retry_config['max_retry_duration'] = max_life
    queue_settings['retry_config'] = retry_config
    parent = f"projects/{PROJECT_ID}/locations/{PROJECT_REGION}"
    try:
        q = client.create_queue(parent=parent, queue=queue_settings)
        app.logger.info("============ CREATED QUEUE ============")
        app.logger.info(q)
    except AlreadyExists as exists:
        app.logger.info(f"Already Exists on get/create/update {short_queue_name} ")
        app.logger.info(exists)
        q = full_queue_name
    except ValueError as error:
        app.logger.info(f"Value Error on get/create/update the {short_queue_name} ")
        app.logger.error(error)
        q = None
    except GoogleAPICallError as error:
        app.logger.info(f"Google API Call Error on get/create/update {short_queue_name} ")
        app.logger.error(error)
        q = None
    return full_queue_name if q else None


def get_or_create_queue(queue_name, logging=0):
    """Updated process for queue path. """
    # parent = client.queue_path(PROJECT_ID, PROJECT_REGION, queue_name)
    # if queue_name in CAPTURE_IMAGE_QUEUE_NAMES:
    #     is_capture = True
    #     queue_name = f"{CAPTURE_QUEUE}-{queue_name}".lower()
    #     routing_override = {'service': CAPTURE_SERVICE}
    # else:
    #     is_capture = False
    #     queue_name = f"{COLLECT_QUEUE}-{queue_name}".lower()
    #     routing_override = {'service': COLLECT_SERVICE}
    # queue_path = client.queue_path(PROJECT_ID, PROJECT_REGION, queue_name)
    # try:
    #     q = client.get_queue(name=queue_path)
    # except Exception as e:
    #     app.logger.info(f"The {queue_path} queue does not exist, or could not be found. Attempting to create it. ")
    #     app.logger.info(e)
    #     q = None
    # if q:
    #     return queue_path
    # rate_limits = {'max_concurrent_dispatches': 2 if is_capture else 1, 'max_dispatches_per_second': 1}
    # rate_limits = RateLimits(**rate_limits)
    # min_backoff, max_backoff, max_life = duration_pb2.Duration(), duration_pb2.Duration(), duration_pb2.Duration()
    # min_backoff.FromJsonString('10s')    # 10 seconds
    # max_backoff.FromJsonString('5100s')  # 1 hour and 25 minutes
    # max_life.FromJsonString('86100s')    # 5 minutes shy of 24 hours
    # retry_config = {'max_attempts': 25, 'min_backoff': min_backoff, 'max_backoff': max_backoff, 'max_doublings': 9}
    # retry_config['max_retry_duration'] = max_life
    # retry_config = RetryConfig(**retry_config)
    # queue_settings = {'name': queue_path, 'rate_limits': rate_limits, 'retry_config': retry_config}
    # if routing_override:
    #     queue_settings['app_engine_routing_override'] = target.AppEngineRouting(**routing_override)
    # if logging:
    #     queue_settings['stackdriver_logging_config'] = StackdriverLoggingConfig(sampling_ratio=logging)
    # queue_settings = Queue(**queue_settings)
    # if queue_path not in list_queues():
    #     queue = client.create_queue(parent=parent, queue=queue_settings)
    # else:
    #     queue = queue_path
    # return queue
    pass


def list_queues():
    """Helper to list the queues associated with this project. """
    parent = f"projects/{PROJECT_ID}/locations/{PROJECT_REGION}"
    queue_list = [ea for ea in client.list_queues(parent=parent)]
    for ea in queue_list:
        app.logger.info(ea)
    return queue_list


def add_to_capture(post, queue_name='test-on-db-b', task_name=None, in_seconds=90):
    """Adds a task to a Capture Queue to send a POST request to the Capture API. Sets where the report is sent back """
    mod = 'post'
    if not isinstance(task_name, (str, type(None))):
        raise TypeError("Usually the task_name for add_to_capture should be None, but should be a string if set. ")
    parent = get_queue_path(queue_name)
    capture_api_path = f"/api/v1/{mod}/"
    report_settings = {'service': environ.get('GAE_SERVICE', 'dev'), 'relative_uri': url_for('capture_report')}
    source = {'queue_type': queue_name, 'queue_name': parent, 'object_type': mod, 'service': CURRENT_SERVICE}
    if isinstance(post, (int, str)):
        post = Post.query.get(post)
    if not isinstance(post, Post):
        raise TypeError("Expected a valid Post object or an id for an existing Post for add_to_capture. ")
    data = {'target_url': post.permalink, 'media_type': post.media_type, 'media_id': post.media_id}
    payload = {'report_settings': report_settings, 'source': source, 'dataset': [data]}
    task = {
            'app_engine_http_request': {  # Specify the type of request.
                'http_method': 'POST',
                'relative_uri': capture_api_path,
                'body': json.dumps(payload).encode()  # Task API requires type bytes.
            }
    }
    if task_name:
        task['name'] = task_name.lower()  # The Task API will generate one if it is not set.
    if in_seconds:
        # Convert "seconds from now" into an rfc3339 datetime string, format as timestamp protobuf, add to tasks.
        d = dt.utcnow() + timedelta(seconds=in_seconds)
        timestamp = timestamp_pb2.Timestamp()
        timestamp.FromDatetime(d)
        task['schedule_time'] = timestamp
    return try_task(parent, task)


def add_to_collect(media_data, process='basic', task_name=None, in_seconds=180):
    """Add tasks to a specific (depending on process) Collect Queue to request Graph API data on media posts.
    Input media_data: Expected get_media_lists output, a list of dicts for each User (containing a list of media info).
    Input process: Indicates if the task is to get the 'basic' post content, the 'metrics', or (data?)
    Input task_name: Usually not set, available for further expansion.
    Input in_seconds: The first task will be scheduled this number of seconds from now.
    Consequences: A task is created for each User in the media_data (later, a Graph API call for each media post).
    Output: A list for each attempted task. Each will be the create task response, or None for caught exceptions.
    """
    mod = 'post'
    if process not in COLLECT_PROCESS_ALLOWED:
        info = f"Unknown process name: {process} "
        app.logger.error(info)
        raise ValueError(info)
    if not isinstance(task_name, (str, type(None))):
        raise TypeError("Usually the task_name for add_to_capture should be None, but should be a string if set. ")
    parent = get_queue_path(process)
    relative_uri = url_for('collect_queue', mod=mod, process=process)  # f"/collect/{mod}/{process}"
    source = {'queue_type': process, 'queue_name': parent, 'service': CURRENT_SERVICE}  # Only used for debugging.
    # data = {'user_id': int, 'post_ids': [int, ] | None, 'media_ids': [int, ] | None, }  # must have post or media ids
    # optional in data: 'metrics': str|None, 'post_metrics': {int: str}|str|None
    timestamp = timestamp_pb2.Timestamp()
    d = dt.utcnow() + timedelta(seconds=in_seconds)
    delay = timedelta(seconds=BETWEEN_COLLECT)
    if isinstance(media_data, dict):  # Normalizes input for a single user to match a list of users.
        media_data = [media_data]
    task_list = []
    for data in media_data:  # There is a data for each User in this batch of media_data.
        # data format: {'user_id': user.id, 'media_ids': media_ids, 'media_list': cur}
        source['start_time'] = d.isoformat()  # Must be serializable.
        for data in batch['media_list']:
            for k, v in data.items():
                if isinstance(v, dt):
                    data[k] = v.isoformat()
        payload = {'source': source, 'dataset': batch}
        task = {
                'app_engine_http_request': {  # Specify the type of request.
                    'http_method': 'POST',
                    'relative_uri': relative_uri,
                    'body': json.dumps(payload).encode()  # Task API requires type bytes.
                }
        }
        if task_name:
            task['name'] = task_name.lower()  # The Task API will generate one if it is not set.
        # Convert "seconds from now" into an rfc3339 datetime string, format as timestamp protobuf, add to tasks.
        timestamp.FromDatetime(d)
        task['schedule_time'] = timestamp
        d = d + delay
        task_list.append(try_task(parent, task))
    return task_list
