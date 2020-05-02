from flask import current_app as app
from sqlalchemy import event
from .model_db import User, Post, db
from .api import install_app_on_user_for_story_updates
from .create_queue_task import add_to_capture


@event.listens_for(User.page_token, 'set', retval=True)
def handle_user_page(user, value, oldvalue, initiator):
    """ Triggered when a value is being set for User.page_token """
    app.logger.debug("================ The page_token listener function is running ===============")
    if value in (None, ''):
        user.story_subscribed = False
        app.logger.debug(f"Empty page_token for {user} user. Set story_subscribed to False. ")
        return None
    if 'subscribe_page' in db.session.info:
        db.session.info['subscribe_page'].add(user)
    else:
        db.session.info['subscribe_page'] = {user}
    return value


@event.listens_for(Post.media_type, 'set', retval=True)
def enqueue_capture(model, value, oldvalue, initiator):
    """ Triggered when a value is being set for Post.media_type.
        Unfortunately we can not be certain the other needed fields have been set for this Post model.
        To make sure this Post gets placed in the appropriate Task queue, it is stored with a key in the session.info.
        Another listener will see all Post models prepared for a Capture queue, and will assign them accordingly.
    """
    value = value.upper()
    no_val = "symbol('NO_VALUE')"
    is_manual, is_new_story, message = False, False, ''
    if str(type(initiator)) != "<class 'sqlalchemy.orm.attributes.Event'>":
        message += "Manually requested capture. "
        is_manual = True
    elif value == 'STORY' and not any([getattr(model, 'saved_media', None), getattr(model, 'capture_name', None)]):
        message += "Triggered by Event. "
        is_new_story = True
    elif value != 'STORY':
        # Posts without 'STORY' set for media_type are not added for capture unless it was a manual request. Not logged.
        return value

    if is_manual or is_new_story:
        capture_type = 'story_capture' if value == 'STORY' else 'post_capture'
        app.logger.debug(f"========== Adding a {capture_type} with enqueue_capture function. {message} ==========")
        # TODO: Fix the next line with the oldvalue we get on new Model instances.
        message += f"New {value} post. " if str(oldvalue) == no_val else f"media_type {oldvalue} to {value}. "
        message += f"When session is committed, will send to {capture_type} Queue. "
        if capture_type in db.session.info:
            db.session.info[capture_type].add(model)
        else:
            db.session.info[capture_type] = {model}
    elif value == 'STORY':
        app.logger.debug(f"========== Running enqueue_capture function. {message} ==========")
        message += f"Did not add {model} because it has already been captured or queued for capture. "
    app.logger.debug(message)
    app.logger.debug('---------------------------------------------------')
    return value


@event.listens_for(db.session, 'before_flush')
def process_session_before_flush(session, flush_context, instances):
    """ During creation or modification of Post models, some may be marked for adding to a Capture queue. """
    app.logger.debug("================ Process Session Before Flush ===============")
    stories_to_capture = session.info.get('story_capture', [])
    other_posts_to_capture = session.info.get('post_capture', [])
    subscribe_pages = session.info.get('subscribe_page', [])
    message = f"Story Captures: {len(stories_to_capture)} Other Captures: {len(other_posts_to_capture)} "
    message += f"Subscribe Pages: {len(subscribe_pages)} \n"
    for story in list(stories_to_capture):
        capture_response = add_to_capture(story)
        if capture_response:
            message += f"Adding to Story capture queue: {str(story)} \n"
            story.capture_name = getattr(capture_response, 'name', None)
            session.info['story_capture'].discard(story)
        else:
            message += f"Failed to add {str(story)} To Capture Story queue. \n"
    for post in list(other_posts_to_capture):
        capture_response = add_to_capture(post, queue_name='post')
        if capture_response:
            message += f"Adding to Post capture queue: {str(post)} \n"
            post.capture_name = getattr(capture_response, 'name', None)
            session.info['post_capture'].discard(post)
        else:
            message += f"Failed to add {str(post)} to Capture Post queue. \n"
    for user in list(subscribe_pages):
        success = install_app_on_user_for_story_updates(user)
        message += f"Subscribe {getattr(user, 'page_id', 'NA')} page for {user} worked: {success} \n"
        user.story_subscribed = success
        if success:
            session.info['subscribe_page'].discard(user)
    # TODO: Handle deletion of Posts not assigned to a Campaign when deleting a User.
    # session.deleted  # The set of all instances marked as 'deleted' within this Session
    app.logger.debug(message)
    app.logger.debug(session.info)
    app.logger.debug('---------------------------------------------------')
