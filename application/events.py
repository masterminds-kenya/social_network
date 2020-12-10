from flask import current_app as app
from sqlalchemy import event
from .model_db import User, Post, Campaign, db
from .api import install_app_on_user_for_story_updates, remove_app_on_user_for_story_updates
from .create_queue_task import add_to_capture

CAPTURE_FEATURE_ACTIVE = False


def session_user_subscribe(user, remove=False):
    """Enqueue user to change their 'story_subscribed' property. Does NOT check if user has active campaigns. """
    add, drop = 'subscribe_page', 'unsubscribe_page'
    if remove:
        add, drop = drop, add
    if add in db.session.info:
        db.session.info[add].add(user)
    else:
        db.session.info[add] = {user, }
    if remove in db.session.info:  # and user in db.session.info[remove]:
        db.session.info[remove].discard(user)
    return user


@event.listens_for(User.page_token, 'set', retval=True)
def handle_user_page(user, value, oldvalue, initiator):
    """ Triggered when a value is being set for User.page_token """
    # app.logger.info("============ The page_token listener function is running ============")
    if value in (None, ''):
        user.story_subscribed = False
        app.logger.info(f"Empty page_token for {user} user. Set story_subscribed to False. ")
        return None
    connected_campaigns = user.campaigns + user.brand_campaigns
    has_active_campaign = any(ea.completed is False for ea in connected_campaigns)
    if has_active_campaign:
        # app.logger.info(f"The {user} has an active campaign. Time to subscribe. ")
        session_user_subscribe(user)
    return value


@event.listens_for(Campaign.brands, "bulk_replace")
@event.listens_for(Campaign.users, "bulk_replace")
def handle_campaign_users(campaign, users, initiator):
    """ Triggered when a User is associated with a Campaign. """
    app.logger.info(f"============ campaign relations: {getattr(initiator, 'impl', initiator)} ============")
    oldvalue = getattr(campaign, initiator.key, None)
    # app.logger.info(f"Initiator Slots: {initiator.__slots__} ")
    # app.logger.info(f"Initiator impl: {getattr(initiator, 'impl', 'NOT FOUND')} ")
    # app.logger.info(f"Initiator key: {getattr(initiator, 'key', 'NOT FOUND')} ")
    # app.logger.info(f"Initiator op: {getattr(initiator, 'op', 'NOT FOUND')} ")
    # app.logger.info(f"Initiator parent_token: {getattr(initiator, 'parent_token', 'NOT FOUND')} ")
    # app.logger.info("----------------------------------------")
    # app.logger.info(f"Campaign: {campaign} ")
    # app.logger.info(f"New Value: {users} ")
    # app.logger.info(f"Old Value: {oldvalue or 'NOT FOUND'} ")
    oldset = set(oldvalue or [])
    newset = set(users)
    new_subscribes = [session_user_subscribe(u) for u in newset - oldset if not u.story_subscribed]
    new_removes = [session_user_subscribe(u, remove=True) for u in oldset - newset if not u.has_active(campaign)]
    app.logger.info(f"New Subscribe: {new_subscribes} ")
    app.logger.info(f"New Removes:   {new_removes} ")
    app.logger.info(f"------------ End relations: {getattr(initiator, 'key', initiator.impl)} ------------")
    return users


@event.listens_for(Campaign.completed, 'set', retval=True)
def handle_campaign_stories(campaign, value, oldvalue, initiator):
    """ Triggered when a Campaign is marked completed. """
    app.logger.info(f"************** Campaign Listener: {getattr(initiator, 'impl', initiator)} **************")
    if value == oldvalue:
        return value
    related_users = getattr(campaign, 'users', []) + getattr(campaign, 'brands', [])
    for user in related_users:
        if value is True:
            if user.story_subscribed and not user.has_active(campaign):
                app.logger.info(f"The {user} is being removed for completed {campaign} ")
                session_user_subscribe(user, remove=True)
        else:
            has_token = getattr(user, 'page_token', None)
            if has_token and not user.story_subscribed:
                app.logger.info(f"The {user} is being subscribed for NOT completed {campaign} ")
                session_user_subscribe(user)
    app.logger.info("---------- Campaign Listener DONE ----------")
    return value


@event.listens_for(Post.media_type, 'set', retval=True)
def enqueue_capture(model, value, oldvalue, initiator):
    """ Triggered when a value is being set for Post.media_type. Can also be initiated as a manual request for a Post.
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
    app.logger.info(message)
    # app.logger.info('---------------------------------------------------')
    return value


@event.listens_for(db.session, 'before_flush')
def process_session_before_flush(session, flush_context, instances):
    """ During creation or modification of Post models, some may be marked for adding to a Capture queue. """
    app.logger.info("============ Process Session Before Flush ===============")
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
    app.logger.info(message)
    app.logger.info(session.info)
    app.logger.info('---------------- End pre-flush session process ----------------')
