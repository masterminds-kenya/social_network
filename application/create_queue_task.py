from flask import current_app as app
from google.api_core.retry import Retry
# from google.api_core import RetryError
from google.api_core.exceptions import RetryError, AlreadyExists, GoogleAPICallError
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from datetime import timedelta, datetime as dt
from .model_db import Post

# TODO(developer): Uncomment these lines and replace with your values.
PROJECT_ID = app.config.get('PROJECT_ID')
PROJECT_ZONE = app.config.get('PROJECT_ZONE')
CAPTURE_SERVICE = app.config.get('CAPTURE_SERVICE')
CAPTURE_QUEUE = app.config.get('CAPTURE_QUEUE', 'test')
# Create a client & construct the fully qualified queue name.
client = tasks_v2.CloudTasksClient()


def get_capture_queue(queue_name):
    """ Creates or Updates a queue for managing calls to the capture API to get the live images of a web page. """
    if not queue_name:
        queue_name = 'test'
    queue_name = f"{CAPTURE_QUEUE}-{queue_name}".lower()
    routing_override = {'service': CAPTURE_SERVICE}
    rate_limits = {'max_concurrent_dispatches': 2, 'max_dispatches_per_second': 1}
    queue_settings = {'name': queue_name, 'app_engine_routing_override': routing_override, 'rate_limits': rate_limits}
    # retry_config ={'max_attempts': 25, 'max_retry_duration': '24h', 'min_backoff': '10', 'max_backoff': '5100', 'max_doublings': 9}
    capture_retry = Retry(initial=10.0, maximum=5100.0, multiplier=9.0, deadline=86100.0)
    parent = client.location_path(PROJECT_ID, PROJECT_ZONE)  # CAPTURE_SERVICE ?
    # parent = f"projects/{PROJECT_ID}/locations/{PROJECT_ZONE}"  # CAPTURE_SERVICE ?
    try:
        # q = client.create_queue(parent, queue_name, retry=capture_retry)
        q = client.update_queue(parent, queue_settings, retry=capture_retry)
    except AlreadyExists as exists:
        # return the existing queue.
        app.logger.debug(f"Already Exists on get/create/update {queue_name} ")
        app.logger.debug(exists)
        q = None
    except ValueError as error:
        app.logger.debug(f"Value Error on get/create/update the {queue_name} ")
        app.logger.error(error)
        q = None
    except GoogleAPICallError as error:
        app.logger.debug(f"Google API Call Error on get/create/update {queue_name} ")
        app.logger.error(error)
        q = None
    queue_path = f"{parent}/queues/{queue_name}" if q else None
    return queue_path


def add_to_capture(post, queue_name='test', task_name=None, payload=None, in_seconds=60):
    """ Will add a task with the given payload to the Capture Queue. """
    if isinstance(post, (int, str)):
        pass
    if not isinstance(post, Post):
        raise TypeError("Expected a Post object or a Post id. ")
    capture_api_path = f"/api/v1/post/{str(post.id)}/{post.media_type.lower()}/{str(post.media_id)}/"
    # task_parent = client.queue_path(PROJECT_ID, PROJECT_ZONE, CAPTURE_QUEUE)
    parent = get_capture_queue(queue_name)
    # Construct the request body.
    task = {
            'app_engine_http_request': {  # Specify the type of request.
                'http_method': 'POST',
                'relative_uri': capture_api_path
            }
    }
    if payload is not None:
        # The API expects a payload of type bytes, and add the payload to the request.
        task['app_engine_http_request']['body'] = payload.encode()
    if task_name:
        # if isinstance(task_name, int):
        #     task_name = str(task_name)
        if not isinstance(task_name, str):
            raise TypeError("The task_name should be a string, or None. ")
        task['name'] = task_name.lower()
    if in_seconds:
        # Convert "seconds from now" into an rfc3339 datetime string.
        d = dt.utcnow() + timedelta(seconds=in_seconds)
        # Create Timestamp protobuf and add to the tasks.
        timestamp = timestamp_pb2.Timestamp()
        timestamp.FromDatetime(d)
        task['schedule_time'] = timestamp
    # Use the client to build and send the task.
    try:
        response = client.create_task(parent, task)
    except ValueError as e:
        app.logger.debug(f"Invalid parameters for creating a task: \n {task}")
        app.logger.error(e)
        response = None
    except RetryError as e:
        app.logger.debug(f"Retry Attempts exhausted for a task: \n {task}")
        app.logger.error(e)
        response = None
    except GoogleAPICallError as error:
        app.logger.debug(f"Google API Call Error on creating a task: \n {task}")
        app.logger.error(error)
        response = None
    if response is not None:
        app.logger.debug(f"Created task: {response.name} ")
        app.logger.debug(response)
    return response
