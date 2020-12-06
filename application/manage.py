from flask import flash, redirect, render_template, url_for, request, current_app as app
from flask_login import current_user, login_user
from werkzeug.security import generate_password_hash
from collections import defaultdict
import hmac
import hashlib
import json
from .api import get_basic_post
from .model_db import db, User, Post, Audience
from .model_db import db_read, db_create, db_update, db_delete
from .helper_functions import mod_lookup


def check_hash(signed, payload):
    """ Checks if the 'signed' value is a SHA1 hash made with our app secret and the given 'payload' """
    pre, signed = signed.split('=', 1)
    if pre != 'sha1':
        app.logger.debug("Signed does not look right. ")
        return False
    if isinstance(payload, dict):
        payload = json.dumps(payload).encode()
    elif isinstance(payload, str):
        payload = payload.encode()
    if not isinstance(payload, bytes):
        app.logger.debug("Unable to prepare payload. ")
        return False
    secret = app.config.get('FB_CLIENT_SECRET').encode()
    test = hmac.new(secret, payload, hashlib.sha1).hexdigest()
    if signed == test:
        return True
    return False


def update_campaign(campaign, request):
    """ Handle adding or removing posts assigned to a campaign, as well removing posts from the processing cue. """
    app.logger.info('=========== Update Campaign ==================')
    form_dict = request.form.to_dict(flat=True)
    # Radio Button | Management | Results | Manage Outcome  | Result Outcome
    # accept       |  data.id   |    0    | camp_id = val   | leave alone
    # reject       |    -1      |   -1    | processed       | camp_id = None
    # ignore       |     0      |   -2    | leave alone     | unset process & camp_id
    try:
        data = {int(key.replace('assign_', '')): int(val) for (key, val) in form_dict.items() if val != '0'}
    except ValueError as e:
        app.logger.error("Error in update_campaign, ValueError translating form to data dict. ")
        app.logger.error(e)
        # TODO: ?handle error somehow?
        return False
    modified = Post.query.filter(Post.id.in_(data.keys())).all()
    for post in modified:
        code = data[post.id]
        if code == -2:  # un-process if processed, un-relate if related
            if post in campaign.processed:
                campaign.processed.remove(post)
            if post in campaign.posts:
                campaign.posts.remove(post)
        elif code == -1:  # processed if not processed, un-relate if related
            if post not in campaign.processed:
                campaign.processed.append(post)
            if post in campaign.posts:
                campaign.posts.remove(post)
        elif code > 0:  # process & make related, we know it was neither except in Rejected view was already processed
            # code == campaign.id should be True
            if post not in campaign.processed:  # TODO: ? Needed for relationships & rejected view ?
                campaign.processed.append(post)
            campaign.posts.append(post)
    try:
        db.session.commit()
    except Exception as e:
        app.logger.error("We had an exception on the campaign update commit. ")
        app.logger.exception(e)
        # TODO: handle exception
        return False
    return True


def process_form(mod, request):
    """ Take the request.form and return the appropriate data with modifications as needed for the Model. """
    # If Model has relationship collections set in form, then we must capture these before flattening the input
    # I believe this is only needed for campaigns.
    save = {}
    if mod == 'campaign':
        data = request.form.to_dict(flat=False)
        # capture the relationship collections
        # TODO: I might be missing how SQLAlchemy intends for use to handle related models
        # the following may not be needed, or need to be managed differently
        rel_collections = (('brands', User), ('users', User), ('posts', Post))
        for rel, Model in rel_collections:
            if rel in data:
                model_ids = [int(ea) for ea in data[rel]]
                models = Model.query.filter(Model.id.in_(model_ids)).all()
                save[rel] = models
    data = request.form.to_dict(flat=True)
    if mod in ['login', *User.ROLES]:
        data['role'] = data.get('role', mod)
        # checking, or creating, password hash is handled outside of this function.
        # On User edit, keep the current password if they left the input box blank.
        if not data.get('password'):
            data.pop('password', None)
        # Create IG media_count & followers_count here, then they are associated on User create or update.
        models = []
        for name in Audience.IG_DATA:  # {'media_count', 'followers_count'}
            value = data.pop(name, None)
            if value:
                models.append(Audience(name=name, values=[json.loads(value)]))
        save['audiences'] = models
    data.update(save)  # adds to the data dict if we did save some relationship collections
    # If the form has a checkbox for a Boolean in the form, we may need to reformat.
    # currently I think only Campaign and Post have checkboxes
    bool_fields = {'campaign': 'completed', 'login': 'remember'}
    # TODO: Add logic to find all Boolean fields in models and handle appropriately.
    if mod in bool_fields:
        data[bool_fields[mod]] = True if data.get(bool_fields[mod]) in {'on', True} else False
    return data


def add_edit(mod, id=None):
    """ Adding or Editing a DB record is a similar process handled here. """
    action = 'Edit' if id else 'Add'
    Model = mod_lookup(mod)
    if action == 'Add' and Model == User:
        if not current_user.is_authenticated \
           or current_user.role not in ['admin', 'manager'] \
           or mod != 'brand':
            flash("Using Signup. ")
            return redirect(url_for('signup'))
    app.logger.info(f'------- {action} {mod} ----------')
    if request.method == 'POST':
        data = process_form(mod, request)
        if mod == 'brand' and data.get('instagram_id', '') in ('None', None, ''):
            # TODO: Decide - Should it work for all User.ROLES, or only 'brand'?
            data['instagram_id'] = None  # TODO: Do not overwrite 'instagram_id' if it was left blank.
        # TODO: ?Check for failing unique column fields, or failing composite unique requirements?
        if action == 'Edit':
            password_mismatch = data.get('password', '') != data.get('password-confirm', '')
            if password_mismatch:
                message = "New password and its confirmation did not match. Please try again. "
                flash(message)
                return redirect(request.referrer)
            if Model == User and data.get('password'):
                # if form password field was blank, process_form has already removed the key by now.
                data['password'] = generate_password_hash(data.get('password'))
            try:
                model = db_update(data, id, Model=Model)
            except ValueError as e:
                app.logger.error('------- Came back as ValueError from Integrity Error -----')
                app.logger.exception(e)
                # Possibly that User account exists for the 'instagram_id'
                # If true, then switch to updating the existing user account
                #     and delete this newly created User account that was trying to be a duplicate.
                ig_id = data.get('instagram_id', None)
                found_user = User.query.filter_by(instagram_id=ig_id).first() if ig_id and Model == User else None
                if found_user:
                    found_user_id = getattr(found_user, 'id', None)
                    # TODO: Are we safe from updating the 'instagram_id' on a form?
                    if current_user.facebook_id == found_user.facebook_id:
                        try:
                            model = db_update(data, found_user_id, Model=Model)
                        except ValueError as e:
                            message = "Unable to update existing user. "
                            app.logger.error(f'----- {message} ----')
                            app.logger.exception(e)
                            flash(message)
                            return redirect(url_for('home'))
                        login_user(found_user, force=True, remember=True)
                        db_delete(id, Model=User)
                        flash("You are logged in. ")
                        # this case will follow the normal return for request.method == 'POST'
                    else:
                        message = "You do not seem to match the existing account. "
                        message += "A new account can not be created with those unique values. "
                        message += "If you own the existing account you can try to Login instead. "
                        flash(message)
                        return redirect(url_for('home'))
                else:
                    flash("Please try again or contact an Admin. ")
                    return redirect(url_for('home'))
        else:  # action == 'Add' and request.method == 'POST'
            try:
                model = db_create(data, Model=Model)
            except ValueError as e:
                app.logger.error('------- Came back as ValueError from Integrity Error -----')
                app.logger.exception(e)
                flash("Error. Please try again or contact an Admin. ")
                return redirect(url_for('add', mod=mod, id=id))
        return redirect(url_for('view', mod=mod, id=model['id']))
    # else: request.method == 'GET'
    template, related = 'form.html', {}
    model = db_read(id, Model=Model) if action == 'Edit' else {}
    if mod == 'campaign':
        template = f"{mod}_{template}"
        users = User.query.filter_by(role='influencer').all()
        brands = User.query.filter_by(role='brand').all()
        related['users'] = [(ea.id, ea.name) for ea in users]
        related['brands'] = [(ea.id, ea.name) for ea in brands]
    return render_template(template, action=action, mod=mod, data=model, related=related)


def report_update(reports, Model):
    """ Input is a list of dictionaries, with each being the update values to apply to the 'mod' Model. """
    message, results, had_error = '', [], False
    app.logger.info("===================== report update =====================")
    # TODO: CRITICAL before pushed to production. Confirm the the source of this update.
    if Model != Post:
        message += "The Report process is not available for that data. "
        app.logger.info(message)
        return message, 500
    for report in reports:
        media_id = report.get('media_id', '')
        model = Model.query.filter_by(media_id=media_id).first()
        if not model:
            message += f"Unable to find a Model with matching media_id: {media_id} \n"
            app.logger.error(message)
            had_error = True
            continue
        # Update model
        for k, v in report.items():
            setattr(model, k, v)
        results.append(model)
        message += f"Updated Model in capture_report: {str(model)} \n"
    else:
        message += "The report_update function received no reports. "
    if len(results):
        db.session.commit()
        message += ', '.join([str(model) for model in results])
        message += "\n Updates committed. "
    app.logger.info(message)
    status_code = 422 if had_error else 200
    return message, status_code


def process_hook(req):
    """ We have a confirmed authoritative update on subscribed data of a Story Post. """
    # req: {'object': 'page', 'entry': [{'id': <ig_id>, 'time': 0, 'changes': [{'field': 'name', 'value': 'newnam'}]}]}
    hook_data, data_count = defaultdict(list), 0
    for ea in req.get('entry', [{}]):
        for rec in ea.get('changes', [{}]):
            # obj_type = req.get('object', '')  # likely: page, instagram, user, ...
            val = rec.get('value', {})
            if not isinstance(val, dict):
                val = {'value': val}
            val.update({'ig_id': ea.get('id')})
            hook_data[rec.get('field', '')].append(val)
            data_count += 1
    # app.logger.debug(f"====== process_hook - stories: {len(hook_data['story_insights'])} total: {data_count} ======")
    # pprint(hook_data)
    total, new, modified, message = 0, 0, 0, ''
    for story in hook_data['story_insights']:
        story['media_type'] = 'STORY'
        media_id = story.pop('media_id', None)  # Exists on found, or put back during get_basic_post (even if failed).
        ig_id = story.pop('ig_id', None)
        if media_id:
            total += 1
            model = Post.query.filter_by(media_id=media_id).first()  # Returns none if not in DB
            if model:
                message += f"STORY post UPDATE for user: {model.user} \n"
                # update
                for k, v in story.items():
                    setattr(model, k, v)
                modified += 1
            else:
                # create, but we need extra data about this story Post.
                # if media_id == '17887498072083520':  # This the test data sent by FB console
                #     res = {'user_id': 190, 'media_id': media_id, 'media_type': 'STORY'}
                #     res['timestamp'] = "2020-04-23T18:10:00+0000"
                #     message += "Test update, added to user # 190 "
                # else:
                user = User.query.filter_by(instagram_id=ig_id).first() if ig_id else None
                user = user or object()
                user_id = getattr(user, 'id', None) or "No User"
                message += f"STORY post CREATE for user: {user_id} \n"
                # res = get_basic_post(media_id, user_id=getattr(user, 'id'), token=getattr(user, 'token'))
                # story.update(res)
                model = Post(**story)
                new += 1
            db.session.add(model)
    message += ', '.join([f"{key}: {len(value)}" for key, value in hook_data.items()])
    message += ' \n'
    if modified + new > 0:
        message += f"Updating {modified} and creating {new} Story Posts; Recording data for {total} Story Posts. "
        try:
            db.session.commit()
            response_code = 200
            message += "Database updated. "
        except Exception as e:
            response_code = 401
            message += "Unable to to commit story hook updates to database. "
            app.logger.info(e)
            db.session.rollback()
    else:
        message += "No needed record updates. "
        response_code = 200
    return message, response_code
