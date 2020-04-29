from flask import current_app as app
from sqlalchemy import event
from .model_db import User, Post, db
from .api import install_app_on_user_for_story_updates
from .create_queue_task import add_to_capture
from pprint import pprint  # Temporary for Debug


@event.listens_for(User.page_token, 'set', retval=True)
def handle_user_page(user, value, oldvalue, initiator):
    """ Triggered when a value is being set for User.page_token """
    app.logger.debug("================ The page_token listener function is running! ===============")
    if value in (None, ''):
        user.story_subscribed = False
        app.logger.debug(f"Empty page for {user} user. Set story_subscribed to False. ")
    else:
        page_id = getattr(user, 'page_id', None)
        if not page_id:
            app.logger.debug(f"Invalid page_id: {str(page_id)} for user: {user} ")
            if 'subscribe_page' in db.session.info:
                db.session.info['subscribe_page'].add(user)
            else:
                db.session.info['subscribe_page'] = {user}
            return value
        page = {'id': page_id, 'token': value}
        success = install_app_on_user_for_story_updates(user, page=page)
        user.story_subscribed = success
        app.logger.debug(f"Subscribe {page_id} page for {user} worked: {success} ")
    return value


@event.listens_for(Post.media_type, 'set', retval=True)
def enqueue_capture(model, value, oldvalue, initiator):
    """ Triggered when a value is being set for Post.media_type.
        Unfortunately we can not be certain the other needed fields have been set for this Post model.
        To make sure this Post gets placed in the appropriate Task queue, it is stored with a key in the session.info.
        Another listener will see all Post models prepared for a Capture queue, and will assign them accordingly.
    """
    message = ''
    if str(type(initiator)) != "<class 'sqlalchemy.orm.attributes.Event'>":
        message += "Manually requested capture. "
        # if 'post_capture' in db.session.info:
        #     db.session.info['post_capture'].add(model)
        # else:
        #     db.session.info['post_capture'] = {model}
    else:
        message += "Triggered by Event. "

    if value == 'STORY':
        app.logger.debug("================ The enqueue_capture function is running! ===============")
        message += "We have a STORY post! "
        message += "It is new! " if oldvalue != 'STORY' else f"Old Value: {oldvalue} . "
        if not getattr(model, 'saved_media', None) and not getattr(model, 'capture_name', None):
            message += "We need to send it for CAPTURE! "
            if 'story_capture' in db.session.info:
                db.session.info['story_capture'].add(model)
            else:
                db.session.info['story_capture'] = {model}
        else:
            message += "Apparently we already have saved_media captured? "
    # else:
    #     message += f"The Post.media_type value is: {value}, with old value: {oldvalue} . "
        app.logger.debug(message)
        app.logger.debug('---------------------------------------------------')
    return value


@event.listens_for(db.session, 'before_flush')  # after_flush, after_flush_postexec
def process_session_before_flush(session, flush_context, instances):
    """ During creation or modification of Post models, some may be marked for adding to a Capture queue. """
    app.logger.debug("================ The process session subscribes is running! ===============")
    # app.logger.debug('session')
    # pprint(dir(session))
    # app.logger.debug('flush_context')
    # pprint(dir(flush_context))
    # app.logger.debug('instances')
    # pprint(instances)
    subscribe_pages = session.info.get('subscribe_page', [])
    report = f"Subscribe Pages: {len(subscribe_pages)} "
    app.logger.debug(report)
    for user in list(subscribe_pages):
        success = install_app_on_user_for_story_updates(user)
        app.logger.debug(f"Subscribe {getattr(user, 'page_id', 'NA')} page for {user} worked: {success} ")
        user.story_subscribed = success
        if success:
            session.info['subscribe_page'].discard(user)
    # TODO: Handle deletion of Posts not assigned to a Campaign when deleting a User.
    # session.deleted  # The set of all instances marked as 'deleted' within this Session
    app.logger.debug('---------------------------------------------------')


@event.listens_for(db.session, 'after_flush_postexec')  # before_flush, after_flush,
def process_session_after_db_response(session, flush_context):
    """ During creation or modification of Post models, some may be marked for adding to a Capture queue. """
    app.logger.debug("================ The process session info is running! ===============")
    pprint(session.info)
    # app.logger.debug('session')
    # pprint(dir(session))
    # app.logger.debug('flush_context')
    # pprint(dir(flush_context))
    message = ''
    stories_to_capture = session.info.get('story_capture', [])
    other_posts_to_capture = session.info.get('post_capture', [])
    subscribe_pages = session.info.get('subscribe_page', [])
    report = f"Story Captures: {len(stories_to_capture)} Other Captures: {len(other_posts_to_capture)} "
    report += f"Pages: {len(subscribe_pages)} "
    app.logger.debug(report)
    for story in list(stories_to_capture):
        message += f"Adding to story capture queue: {story} \n"
        capture_response = add_to_capture(story)
        if capture_response:
            story.capture_name = getattr(capture_response, 'name', None)
            session.info['story_capture'].discard(story)
        else:
            app.logger.debug(message)
            message += f"Capture did not work for {story} Post. "
            raise Exception(message)
    app.logger.debug(message)
    for post in list(other_posts_to_capture):
        capture_response = add_to_capture(post, queue_name='post')
        if capture_response:
            post.capture_name = getattr(capture_response, 'name', None)
            session.info['post_capture'].discard(post)
        else:
            app.logger.error(f"Capture Post did not work for {str(post)} Post. ")
    # for user in subscribe_pages:
    #     success = install_app_on_user_for_story_updates(user)
    #     app.logger.debug(f"Subscribe {getattr(user, 'page_id', 'NA')} page for {user} worked: {success} ")
    #     user.story_subscribed = success
    #     if success:
    #         session.info['subscribe_page'].discard(user)
    # TODO: Handle deletion of Posts not assigned to a Campaign when deleting a User.
    # session.deleted  # The set of all instances marked as 'deleted' within this Session
    app.logger.debug('---------------------------------------------------')
    pprint(session.info)
