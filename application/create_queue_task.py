from flask import current_app as app
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from datetime import timedelta, datetime as dt

# TODO(developer): Uncomment these lines and replace with your values.
PROJECT_ID = app.config.get('PROJECT_ID')
PROJECT_ZONE = app.config.get('PROJECT_ZONE')
CAPTURE_QUEUE = app.config.get('CAPTURE_QUEUE')
target = app.config.get('CAPTURE_SERVICE', '')
# Create a client & construct the fully qualified queue name.
client = tasks_v2.CloudTasksClient()
parent = client.queue_path(PROJECT_ID, PROJECT_ZONE, CAPTURE_QUEUE)


def add_to_capture(payload, in_seconds=None):
    """ Will add a task with the given payload to the Capture Queue. """
    # Construct the request body.
    task = {
            'app_engine_http_request': {  # Specify the type of request.
                'http_method': 'POST',
                'relative_uri': '/example_task_handler'
            }
    }
    # payload = request.get_json()
    if payload is not None:
        # The API expects a payload of type bytes, and add the payload to the request.
        task['app_engine_http_request']['body'] = payload.encode()
    if in_seconds:
        # Convert "seconds from now" into an rfc3339 datetime string.
        d = dt.utcnow() + timedelta(seconds=in_seconds)
        # Create Timestamp protobuf and add to the tasks.
        timestamp = timestamp_pb2.Timestamp()
        timestamp.FromDatetime(d)
        task['schedule_time'] = timestamp
    # Use the client to build and send the task.
    response = client.create_task(parent, task)
    app.logger.debug(f"Created task: {response.name} ")
    app.logger.debug(response)
    return response
