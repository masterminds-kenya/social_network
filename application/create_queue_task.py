from flask import current_app as app
from google.api_core.retry import Retry
# from google.api_core import RetryError
from google.api_core.exceptions import RetryError, AlreadyExists, GoogleAPICallError
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from datetime import timedelta, datetime as dt
from .model_db import Post
from pprint import pprint

# TODO(developer): Uncomment these lines and replace with your values.
PROJECT_ID = app.config.get('PROJECT_ID')
PROJECT_REGION = app.config.get('PROJECT_REGION')  # Google Docs said PROJECT_ZONE ?
CAPTURE_SERVICE = app.config.get('CAPTURE_SERVICE')
CAPTURE_QUEUE = app.config.get('CAPTURE_QUEUE', 'test')
# Create a client & construct the fully qualified queue name.
client = tasks_v2.CloudTasksClient()


def get_capture_queue(queue_name):
    """ Creates or Updates a queue for managing calls to the capture API to get the live images of a web page. """
    if not queue_name:
        queue_name = 'test'
    queue_name = f"{CAPTURE_QUEUE}-{queue_name}".lower()
    parent = client.location_path(PROJECT_ID, PROJECT_REGION)  # f"projects/{PROJECT_ID}/locations/{PROJECT_REGION}"
    queue_path = client.queue_path(PROJECT_ID, PROJECT_REGION, queue_name)
    routing_override = {'service': CAPTURE_SERVICE}
    rate_limits = {'max_concurrent_dispatches': 2, 'max_dispatches_per_second': 1}
    # retry_config ={'max_attempts': 25, 'min_backoff': '10', 'max_backoff': '5100', 'max_doublings': 9}
    # retry_config['max_retry_duration'] = '24h'
    queue_settings = {'name': queue_path, 'app_engine_routing_override': routing_override, 'rate_limits': rate_limits}
    capture_retry = Retry(initial=10.0, maximum=5100.0, multiplier=9.0, deadline=86100.0)
    app.logger.debug("================= get_capture_queue: queue_settings ===========================")
    pprint(queue_settings)
    try:
        q = client.create_queue(parent, queue_settings, retry=capture_retry)
        # q = client.update_queue(queue_settings, retry=capture_retry)
    except AlreadyExists as exists:
        # TODO: return the existing queue.
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
    # queue_path = f"{parent}/queues/{queue_name}" if q else None
    return queue_path if q else None


def add_to_capture(post, queue_name='testing', task_name=None, payload=None, in_seconds=90):
    """ Will add a task to the Capture Queue with a POST request if given a payload, else with GET request. """
    if not isinstance(task_name, (str, type(None))):
        raise TypeError("The task_name for add_to_capture should be a string, or None. ")
    if isinstance(post, (int, str)):
        post = Post.query.get(post)
    if not isinstance(post, Post):
        raise TypeError("Expected a valid Post object or a Post id for add_to_capture. ")
    app.logger.debug(f"id: {post.id} media_type: {post.media_type} media_id: {post.media_id} ")
    parent = get_capture_queue(queue_name)
    #  API URL format:
    #  /api/v1/post/[id]/[media_type]/[media_id]/?url=[url-to-test-for-images]
    #  Expected JSON response has the following properties:
    #  'success', 'message', 'file_list', url_list', 'error_files', 'deleted'
    capture_api_path = f"/api/v1/post/{str(post.id)}/{str(post.media_type).lower()}/{str(post.media_id)}/"
    capture_api_path += f"?url={str(post.permalink)}"
    # Construct the request body.
    http_method = 'POST' if payload else 'GET'
    task = {
            'app_engine_http_request': {  # Specify the type of request.
                'http_method': http_method,
                'relative_uri': capture_api_path
            }
    }
    if payload is not None:
        task['app_engine_http_request']['body'] = payload.encode()  # Add payload to request as required type bytes.
    if task_name:
        task['name'] = task_name.lower()  # The Task API will generate one if it is not set.
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
