from flask import current_app as app
import json
from .model_db import create_many, db_read
from .api import get_ig_info

USER_FILE = 'env/user_save.txt'


def load():
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


def capture(post, filename):
    """ Visits the permalink for give Post, creates a screenshot named the given filename. """
    ig_url, answer = post.permalink, 'None. '
    app.logger.debug('========== Capture Media Files ==========')
    app.logger.debug(ig_url)
    # answer = chrome_grab(ig_url, filename)
    # answer = phantom_grab(ig_url, filename)
    # answer = soup_no_chrome(ig_url, filename)
    return answer
