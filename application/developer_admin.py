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
    try:
        for user in users:
            value = getattr(user, 'token')
            app.logger.debug(value)
            setattr(user, 'crypt', value)
            count += 1
        message += f"Adjusted for {count} users. "
        db.session.commit()
        message += "Commit Finished! "
    except Exception as e:
        temp = f"Encrypt method error. Count: {count}. "
        app.logger.error(temp)
        app.logger.exception(e)
        message += temp
        db.session.rollback()
    return message
