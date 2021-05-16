from flask import current_app as app
# from flask.helpers import stream_with_context
from sqlalchemy import event
# from flask_login import user_logged_in, user_unauthorized, session_protected, user_logged_out, current_user
from .model_db import User, Post, Campaign, db
from .api import install_app_on_user_for_story_updates, remove_app_on_user_for_story_updates
from .create_queue_task import add_to_capture

CAPTURE_FEATURE_ACTIVE = False


# def heard_user(sender, user):
#     app.logger.info("========== HEARD USER ==========")
#     app.logger.info(f"Had user_logged_in signal for: {user} ")
#     app.logger.info(f"The sender: {sender} ")


# def bad_user(sender):

#     pass


# def sess_protect(sender):
#     app.logger.info("========== SESS PROTECT ==========")
#     app.logger.info(f"The sender: {sender} ")


# def bye_user(sender, user):
#     app.logger.info("========== GOODBYE USER ==========")
#     app.logger.info(f"Had user_logged_out signal for: {user} ")
#     app.logger.info(f"The sender: {sender} ")


# user_logged_in.connect(heard_user, app)
# user_unauthorized.connect(bad_user, app)
# session_protected.connect(sess_protect, app)
# user_logged_out.connect(bye_user, app)


def session_user_subscribe(user, remove=False):
    """Enqueue user to change their 'story_subscribed' property. Does NOT check if user has active campaigns. """
    add, drop = 'subscribe_page', 'unsubscribe_page'
    if remove:
        add, drop = drop, add
    if add in db.session.info:
        db.session.info[add].add(user)
    else:
        db.session.info[add] = {user, }
    if remove in db.session.info:
        db.session.info[remove].discard(user)  # Ignored if not present in the set.
    return user


@event.listens_for(User.page_token, 'set', retval=True)
def handle_user_page(user, value, oldvalue, initiator):
    """Triggered when a value is being set for User.page_token """
    app.logger.debug("============ Listener page_token for %s ============", str(user))
    if value in (None, ''):
        user.story_subscribed = False
        app.logger.debug("Empty page_token for %s user. Set story_subscribed to False. ", str(user))
        return None
    if user.has_active_all:
        app.logger.debug("The %s has an active campaign. Set to subscribe. ", str(user))
        session_user_subscribe(user)
    return value


@event.listens_for(Campaign.brands, "bulk_replace")
@event.listens_for(Campaign.users, "bulk_replace")
def handle_campaign_users(campaign, users, initiator):
    """Triggered when a User is associated with a Campaign. """
    app.logger.debug("============ campaign related: %s ============", getattr(initiator, 'impl', initiator))
    oldvalue = getattr(campaign, initiator.key, None)
    # app.logger.debug("Initiator Slots: %s ", initiator.__slots__)  # ('impl', 'key', 'op', parent_token, ... ?)
    oldset = set(oldvalue or [])
    newset = set(users)
    new_subscribes = [session_user_subscribe(u) for u in newset - oldset if not u.story_subscribed]
    new_removes = [session_user_subscribe(u, remove=True) for u in oldset - newset if not u.has_active(campaign)]
    app.logger.debug("New Subscribe: %s ", new_subscribes)
    app.logger.debug("New Removes:   %s ", new_removes)
    app.logger.debug("--------- End related: %s ---------", getattr(initiator, 'key', getattr(initiator, 'impl', 'XX')))
    return users


@event.listens_for(Campaign.completed, 'set', retval=True)
def handle_campaign_stories(campaign, value, oldvalue, initiator):
    """Triggered when a Campaign is marked completed. """
    app.logger.debug("************** Campaign Listener: %s **************", getattr(initiator, 'impl', initiator))
    if value == oldvalue:
        return value
    related_users = getattr(campaign, 'users', []) + getattr(campaign, 'brands', [])
    for user in related_users:
        if value is True:
            if user.story_subscribed and not user.has_active(campaign):
                app.logger.debug("The %s is being removed for completed %s ", str(user), campaign)
                session_user_subscribe(user, remove=True)
        else:
            has_token = getattr(user, 'page_token', None)
            if has_token and not user.story_subscribed:
                app.logger.debug("The %s is being subscribed for NOT completed %s ", str(user), campaign)
                session_user_subscribe(user)
    app.logger.debug("---------- Campaign Listener DONE ----------")
    return value


@event.listens_for(Post.media_type, 'set', retval=True)
def enqueue_capture(model, value, oldvalue, initiator):
    """Triggered when a value is being set for Post.media_type. Can also be initiated as a manual request for a Post.
        Unfortunately we can not be certain the other needed fields have been set for this Post model.
        To make sure this Post gets placed in the appropriate Task queue, it is stored with a key in the session.info.
        Another listener will see all Post models prepared for a Capture queue, and will assign them accordingly.
    """
    value = value.upper()
    no_val = "symbol('NO_VALUE')"
    is_manual, is_new_story, message = False, False, ''
    if str(type(initiator)) != "<class 'sqlalchemy.orm.attributes.Event'>":
        message += "Manual Capture. "
        is_manual = True
    elif value == 'STORY' and not any([getattr(model, 'saved_media', None), getattr(model, 'capture_name', None)]):
        message += "Event Capture. "
        is_new_story = True
    elif value != 'STORY':
        # Posts without 'STORY' set for media_type are not added for capture unless it was a manual request. Not logged.
        return value

    if is_manual or is_new_story:
        capture_type = 'story_capture' if value == 'STORY' else 'post_capture'
        message += f"New {value}. " if str(oldvalue) == no_val else f"{oldvalue} to {value}. "
        message += f"Queue {capture_type} "
        if not CAPTURE_FEATURE_ACTIVE:
            message += "NOT ACTIVATE "
        if capture_type in db.session.info:
            db.session.info[capture_type].add(model)
        else:
            db.session.info[capture_type] = {model}
    elif value == 'STORY':
        message += f"Expect STORY already queued: {model} "
    app.logger.debug(message)
    return value


@event.listens_for(db.session, 'before_flush')
def process_session_before_flush(session, flush_context, instances):
    """During creation or modification of Post models, some may be marked for adding to a Capture queue. """
    app.logger.debug("============ Process Session Before Flush ===============")
    stories_to_capture = session.info.get('story_capture', [])
    other_posts_to_capture = session.info.get('post_capture', [])
    subscribe_pages = session.info.get('subscribe_page', [])
    remove_pages = session.info.get('unsubscribe_page', [])
    message = f"Story Captures: {len(stories_to_capture)} Other Captures: {len(other_posts_to_capture)} "
    message += f"Remove: {len(remove_pages)} Subscribe: {len(subscribe_pages)} "
    for story in list(stories_to_capture):
        if not CAPTURE_FEATURE_ACTIVE:
            session.info['story_capture'].discard(story)
            continue
        capture_response = add_to_capture(story)
        if capture_response:
            message += f"Adding to Story capture queue: {str(story)} \n"
            story.capture_name = getattr(capture_response, 'name', None)
            session.info['story_capture'].discard(story)
        else:
            message += f"Failed to add {str(story)} To Capture Story queue. \n"
    for post in list(other_posts_to_capture):
        if not CAPTURE_FEATURE_ACTIVE:
            session.info['post_capture'].discard(post)
            continue
        capture_response = add_to_capture(post, queue_name='post')
        if capture_response:
            message += f"Adding to Post capture queue: {str(post)} \n"
            post.capture_name = getattr(capture_response, 'name', None)
            session.info['post_capture'].discard(post)
        else:
            message += f"Failed to add {str(post)} to Capture Post queue. \n"
    for user in list(subscribe_pages):
        success = install_app_on_user_for_story_updates(user)
        message += '\n' + f"Subscribe {getattr(user, 'page_id', 'NA')} page for {user} worked: {success} "
        user.story_subscribed = success
        if success:
            session.info['subscribe_page'].discard(user)
    for user in list(remove_pages):
        success = remove_app_on_user_for_story_updates(user)
        message += '\n' + f"Remove {getattr(user, 'page_id', 'NA')} page for {user} worked: {success} "
        if success:
            user.story_subscribed = not success
            session.info['unsubscribe_page'].discard(user)
    # TODO: Handle deletion of Posts not assigned to a Campaign when deleting a User.
    # session.deleted  # The set of all instances marked as 'deleted' within this Session
    app.logger.debug("===== Process Flush | %s | %s =====", message, session.info)
