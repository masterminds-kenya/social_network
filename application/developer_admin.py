from flask import redirect, render_template, url_for, flash, current_app as app
from flask_login import current_user
import json
from .helper_functions import staff_required, admin_required, mod_lookup
from .model_db import create_many, db_read, User, db
from .api import get_ig_info, get_fb_page_for_user

USER_FILE = 'env/user_save.txt'


def admin_view(data=None, files=None):
    """ Platform Admin view to view links and actions unique to admin """
    dev_email = ['hepcatchris@gmail.com', 'christopherlchapman42@gmail.com']
    dev = current_user.email in dev_email
    # files = None if app.config.get('LOCAL_ENV') else all_files()
    return render_template('admin.html', dev=dev, data=data, files=files)


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


def encrypt_token():
    """ Takes value in token field and saves in encrypt field, triggering the encryption process.
        Function is only for use by dev admin.
    """
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
    from .model_db import Post, OnlineFollowers, Insight
    p_keys = [*Post.METRICS['STORY'].union(Post.METRICS['VIDEO'])]  # All the integer Metrics requested from API.
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


def get_page_for_all_users(overwrite=False, **kwargs):
    """ We need the page number and token in order to setup webhooks for story insights.
        The subscribing to a user's page will be handled elsewhere, and
        triggered by this function when it sets and commits the user.page_token value.
    """
    updates = {}
    q = User.query.filter(User.instagram_id.isnot(None))
    for key, val in kwargs.items():
        if isinstance(val, (list, tuple)):
            q = q.filter(getattr(User, key).in_(val))
        elif isinstance(val, bool):
            q = q.filter(getattr(User, key).is_(val))
        elif isinstance(val, type(None)):
            q = q.filter(getattr(User, key).isnot(None))
        elif isinstance(val, (str, int, float)):
            q = q.filter(getattr(User, key) == val)
        else:
            app.logger.error(f"Unsure how to filter for type {type(val)} for key: value of {key}: {val} ")
    users = q.all()
    app.logger.debug('------------ get page for all users ---------------')
    app.logger.debug(users)
    for user in users:
        page = get_fb_page_for_user(user)
        if page and (overwrite or page.get('new_page')):
            user.page_id = page.get('id')
            user.page_token = page.get('token')
            db.session.add(user)
            updates[user.id] = str(user)
    db.session.commit()
    return updates


@app.route('/<string:mod>/<int:id>/subscribe')
@staff_required()
def subscribe_page(mod, id):
    """ NOT IMPLEMENTED. Used by admin manually subscribe to this user's facebook page. """
    pass


@app.route('/all_users/subscribe')
@staff_required()
def subscribe_all_pages():
    """ DEPRECATED. Used by admin to subscribe to all current platform user's facebook page. """
    from pprint import pprint

    app.logger.info(f"========== subscribe_all_pages ==========")
    column_args = {'story_subscribed': False}
    all_response = get_page_for_all_users(overwrite=True, **column_args)
    # app.logger.debug(f"Installing was successful: {page} ! ")
    pprint(all_response)
    app.logger.info('-------------------------------------------------------------')
    return admin_view(data=all_response)


@app.route('/data/load/')
@admin_required()
def load_user():
    """ DEPRECATED. This is a temporary development function. Will be removed for production. """
    load()
    return redirect(url_for('all', mod='influencer'))


@app.route('/data/<string:mod>/<int:id>')
@admin_required()
def backup_save(mod, id):
    """ DEPRECATED. This is a temporary development function. Will be removed for production. """
    Model = mod_lookup(mod)
    count = save(mod, id, Model)
    message = f"We just backed up {count} {mod} model(s). "
    app.logger.info(message)
    flash(message)
    return redirect(url_for('view', mod='influencer', id=id))


@app.route('/data/encrypt/')
@admin_required()
def encrypt():
    """ DEPRECATED. This is a temporary development function. Will be removed for production. """
    message, success = encrypt_token()
    app.logger.info(message)
    if success:
        success = fix_defaults()
        temp = "Fix defaults worked! " if success else "Had an error in fix_defaults. "
        app.logger.info(temp)
        message += temp
    else:
        message += "Did not attempt fix_defaults. "
    flash(message)
    return admin_view(data=message)
    # return render_template('admin.html', dev=True, data=message, files=None)


@app.route('/deletion')
def fb_delete():
    """ NOT IMPLEMENTED.
        Handle a Facebook Data Deletion Request
        More details: https://developers.facebook.com/docs/apps/delete-data
    """
    response = {}
    response['user_id'] = 'test user_id'
    response['url'] = 'see status of deletion'
    response['confirmation_code'] = 'some unique code'
    # TODO: do stuff
    return json.dumps(response)
