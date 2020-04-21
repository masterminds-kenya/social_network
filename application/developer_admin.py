from flask import current_app as app
import json
from .model_db import create_many, db_read
from .api import get_ig_info

USER_FILE = 'env/user_save.txt'


def load():
    """ Deprecated function.
        Function is only for use by dev admin.
        Takes users saved in text file and puts that data in the database.
    """
    new_users = []
    app.logger.info('------- Load users from File ------------')
    with open(USER_FILE, 'r') as file:
        for line in file.readlines():
            user = json.loads(line)
            # if 'email' in user:
            #     del user['email']
            ig_id, token = user.get('instagram_id'), user.get('token')
            ig_info = get_ig_info(ig_id, token=token)
            user['username'] = ig_info.get('username')
            app.logger.info(user['username'])
            new_users.append(user)
    created_users = create_many(new_users)
    app.logger.info(f'------------- Create from File: {len(created_users)} users -------------')
    return True if len(created_users) else False


def save(mod, id, Model):
    """ Deprecated Function
        Function is only for use by dev admin.
        Takes users in the database and saves them in a text file to later be managed by the load function.
    """
    app.logger.info('------- Save User to File -------')
    if mod in {'brand', 'influencer', 'user'}:
        filename = USER_FILE
    model = db_read(id, Model=Model, safe=False)
    del model['id']
    model.pop('created', None)
    model.pop('modified', None)
    model.pop('insight', None)
    model.pop('audience', None)
    app.logger.info('Old Account: ', model)
    count = 0
    with open(filename, 'a') as file:
        file.write(json.dumps(model))
        file.write('\n')
        count += 1
    return count


def encrypt():
    """ Takes value in token field and saves in encrypt field, triggering the encryption process.
        Function is only for use by dev admin.
    """
    from .model_db import db, User

    message, count = '', 0
    # q = User.query.filter(User.token is not None)
    users = User.query.all()
    app.logger.debug(f"Attempting token encrypt for {len(users)} users. ")
    for user in users:
        value = getattr(user, 'token')
        setattr(user, 'crypt', value)
        count += 1
    app.logger.debug(f"{count} done. ")
    message += f"Adjusted for {count} users. "
    try:
        db.session.commit()
        message += "Commit Finished! "
        success = True
    except Exception as e:
        success = False
        temp = f"Encrypt method error. Count: {count}. "
        app.logger.error(temp)
        app.logger.exception(e)
        message += temp
        db.session.rollback()
    return message, success


def fix_defaults():
    """ Temporary route and function for developer to test components. """
    from .model_db import Post, OnlineFollowers, Insight, db

    p_keys = ['impressions', 'reach', 'engagement', 'saved', 'video_views', 'exits', 'replies', 'taps_forward', 'taps_back']
    # not_needed_keys = ['comments_count', 'like_count', ]
    update_count = 0
    Model = Post
    app.logger.debug(f"========== Test: {Model.__name__} many fields ==========")
    for pkey in p_keys:
        q = Model.query.filter(getattr(Post, pkey).is_(None))
        update_count += q.count()
        q.update({pkey: 0}, synchronize_session=False)
        app.logger.debug(f"----- {pkey} | {update_count} -----")
    app.logger.debug(f"========== updating {update_count} records in Post ==========")
    updates = [(OnlineFollowers, ['value']), (Insight, ['value'])]
    for Model, fields in updates:
        for column in fields:
            models = Model.query.filter(getattr(Model, column).is_(None)).all()
            app.logger.debug(f"--------- Test: {Model.__name__} {column} ----------")
            for model in models:
                setattr(model, column, 0)
                update_count += 1
                db.session.add(model)
    app.logger.debug(f"========= Updating {update_count} total records =========")
    try:
        db.session.commit()
        success = True
    except Exception as e:
        app.logger.error('Had an exception in fix_defaults. ')
        app.logger.error(e)
        success = False
        db.session.rollback()
    return success


def get_page_for_all_users():
    """ We need the page number and token in order to setup webhooks for story insights. """
    from .api import get_fb_page_for_user
    from .model_db import User, db

    updates = {}
    users = User.query.filter(User.instagram_id.isnot(None)).all()
    for user in users:
        page = get_fb_page_for_user(user)
        if page:
            user.page_id = page.get('id')
            user.page_token = page.get('token')
            db.session.add(user)
            updates[user.id] = str(user)
    db.session.commit()
    return updates
