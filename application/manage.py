from flask import flash, redirect, render_template, url_for, request, current_app as app
from flask_login import current_user, login_user
from sqlalchemy.sql.sqltypes import DateTime
from werkzeug.security import generate_password_hash
from collections import defaultdict
from functools import reduce
import hmac
import hashlib
import json
from .model_db import fix_date, db, User, Post, Audience
from .model_db import db_read, db_create, db_update, db_delete
from .helper_functions import mod_lookup, make_missing_timestamp


def check_hash(signed, payload):
    """Checks if the 'signed' value is a SHA1 hash made with our app secret and the given 'payload' """
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
    """Handle adding or removing posts assigned to a campaign, as well as removing posts from the processing Queue. """
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
    """Take the request.form and return the appropriate data with modifications as needed for the Model. """
    # If Model has relationship collections set in form, then we must capture these before flattening the input
    # I believe this is only needed for campaigns.
    save = {}
    if mod == 'campaign':
        data = request.form.to_dict(flat=False)
        # capture the relationship collections
        rel_collections = (('brands', User), ('users', User), ('posts', Post))
        data.setdefault('brands', [])  # No value means user removed the pre-populated value.
        data.setdefault('users', [])  # No value means user removed the pre-populated value.
        for rel, Model in rel_collections:
            if rel in data:
                model_ids = [int(ea) for ea in data[rel]]
                models = Model.query.filter(Model.id.in_(model_ids)).all()
                save[rel] = models
    data = request.form.to_dict(flat=True)
    if mod in ['login', *User.ROLES]:
        data['role'] = data.get('role', mod)  # For mod == 'login', extra keys are never looked up or applied.
        # checking, or creating, password hash is handled outside of this function.
        if not data.get('password'):  # On User edit, keep the current password if they left the input box blank.
            data.pop('password', None)
        # # The audiences (specifically 'media_count' and 'followers_count') do NOT need to be modified in process_form.
        # Create IG media_count & followers_count here, then they are associated on User create or update.
        models = []
        for name in Audience.IG_DATA:  # {'media_count', 'followers_count'}
            value = data.pop(name, None)
            if value:
                models.append(Audience(name=name, values=[json.loads(value)]))
        if models:
            save['audiences'] = models
        # TODO: Confirm that 'audiences' are not overwritten unintentionally.
        # SAFE: login->process_form, signup->process_form, add(only allows 'campaign' or 'brand' mod)->add_edit
        # edit->add_edit: Only mod in ('campaign', *User.ROLES) by admin, manager or self user allowed. is it SAFE?
        # Onboarding: edit->add_edit:
    data.update(save)  # adds to the data dict if we did save some relationship collections
    # If the form has a checkbox for a Boolean in the form, we may need to reformat.
    bool_fields = {'campaign': 'completed', 'login': 'remember'}  # currently only Campaign and Post have checkboxes
    # TODO: Add logic to find all Boolean fields in models and handle appropriately.
    if mod in bool_fields:
        data[bool_fields[mod]] = True if data.get(bool_fields[mod]) in {'on', True} else False
    return data


def add_edit(mod, id=None):
    """Adding or Editing Models. For Campaigns, settings handled here, but all else handled by update_campaign. """
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
            if 'password' in data and 'password-confirm' in data and data['password'] != data['password-confirm']:
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
        related['users'] = User.query.filter_by(role='influencer').all()
        related['brands'] = User.query.filter_by(role='brand').all()
    return render_template(template, action=action, mod=mod, data=model, related=related)


def report_update(reports, Model):
    """Input is a list of dictionaries, with each being the update values to apply to the 'mod' Model. """
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


def media_posts_save(media_results, bulk_db_operation='create', return_ids=False, add_time=False):
    """Use bulk database processes to 'create', 'update', or 'save' Posts based on a list of mapped objects (dicts).
    If return_ids is True, then each dict of post data will be updated with its assigned id in the database.
    The add_time parameter should be True if the post data is being created in the database (vs updated).
    Besides modifying the media_results, this function returns two values: a count of posts, and a success boolean.
    """
    if isinstance(media_results, list) and len(media_results) == 0:
        return 0, True
    if bulk_db_operation == 'create':
        mediaset = reduce(lambda result, ea: result + ea.get('media_list', []), media_results, [])
        args = [Post, mediaset]
        db_process = db.session.bulk_insert_mappings
    elif bulk_db_operation == 'update':
        mediaset = media_results  # For 'update', expect to only have a list of mappings (dicts).
        db_process = db.session.bulk_update_mappings
    elif bulk_db_operation == 'save':  # Will INSERT or UPDATE as needed. Requires a list of Post objects.
        # mediaset = reduce(lambda result, ea: result + ea.get('media_list', []), media_results, [])
        db_process = db.session.bulk_save_objects
        raise NotImplementedError("The UPSERT, or INSERT | UPDATE as needed, feature is not yet implemented. ")
    else:
        raise ValueError(f"Not a valid 'bulk_db_operation' value: {bulk_db_operation}")
    if add_time and bulk_db_operation == 'save':
        raise NotImplementedError("This function is unable to add a timestamp for bulk saving of objects. ")
    if add_time:
        ts = str(make_missing_timestamp(0))
        for d in mediaset:
            d.update(timestamp=ts)
            fix_date(Post, d)
    args = [Post, mediaset] if bulk_db_operation != 'save' else [mediaset]
    kwargs = {'return_defaults': True} if return_ids and bulk_db_operation in ('save', 'create') else {}
    count = len(mediaset)
    try:
        db_process(*args, **kwargs)  # If return_results, the mediaset will be modified.
        db.session.commit()
        success = True
    except Exception as e:
        error_info = f"There was a problem with the bulk '{bulk_db_operation}' process. "
        success = False
        app.logger.error(f"========== MEDIA POSTS {bulk_db_operation} ERROR ==========")
        app.logger.error(error_info)
        app.logger.error(e)
        db.session.rollback()
    if add_time and bulk_db_operation == 'create':
        datefield = 'recorded' if args[0] == Post else 'end_time'
        for data in mediaset:
            data.pop(datefield)
    return count, success


def process_hook(req):
    """We have a confirmed authoritative update on subscribed data of a Story Post. """
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
    story_insights = hook_data.get('story_insights', [])
    insight_count = len(story_insights)
    data_log = f"{insight_count} story"
    if data_count != insight_count:
        data_log += f", {data_count} total"
    # app.logger.info(f"============ PROCESS HOOK: {data_log} ============")
    timestamp = str(make_missing_timestamp(1))  # timestamp = str(dt.utcnow() - 1 day)
    total, new, modified, skipped, message = 0, 0, 0, 0, ''
    for story in story_insights:
        story['media_type'] = 'STORY'
        media_id = story.pop('media_id', None)  # Will be put back if creating, but already exists if updating.
        ig_id = story.pop('ig_id', None)  # Used to find the user if creating.
        total += 1
        if not media_id or not ig_id:
            missed = 'media_id ' if not media_id else 'ig_id'
            missed = 'media_id AND ig_id' if not media_id and not ig_id else missed
            message += f"story_insights missing: {missed} " + '\n'
            app.logger.error(story)
            app.logger.error(f"---------- media_id: {media_id} | ig_id: {ig_id} | SKIP BAD {missed} ----------")
            continue
        model = Post.query.filter_by(media_id=media_id).first()  # Returns none if not in DB
        if model:
            message += f"STORY post UPDATE for user: {getattr(model, 'user', 'UNKNOWN USER')} \n"
            # update
            for k, v in story.items():
                setattr(model, k, v)
            modified += 1
        else:  # We did not see this STORY post in our daily download.
            # create, but we need to fill in some data about this story Post.
            # if media_id == '17887498072083520':  # This the test data sent by FB console
            #     user_id = '190'  # or other testing user_id.
            #     message += f"Test update, added to user # {user_id} "
            # else:
            user = User.query.filter_by(instagram_id=ig_id).first()  # returns None if not found.
            if not user or not user.has_active_all:
                data_log += f", for {user or 'not-found-user'} SKIP"
                skipped += 1
                continue
            user_id = user.id
            story.update(media_id=media_id, user_id=user_id, timestamp=timestamp)
            if 'caption' not in story:
                story['caption'] = 'INSIGHTS_CREATED'
            message += f"STORY post CREATE for user: {user_id} | Timestamp: {timestamp} \n"
            model = Post(**story)
            new += 1
        if not model:
            app.logger.info("Expected a model, but do not have one. ")
        db.session.add(model)
    message += ', '.join([f"{key}: {len(value)}" for key, value in hook_data.items()]) + ' '
    if modified + new > 0:
        message += '\n' + f"STORY posts: update {modified}, create {new}, TOTAL {total}. "
        try:
            db.session.commit()
            response_code = 200
            message += "Database updated. "
        except Exception as e:
            response_code = 401
            message += "Unable to to commit story hook updates to database. "
            app.logger.info(e)
            db.session.rollback()
    elif total == skipped:
        message = ''
        response_code = 200
    else:
        message += "No needed record updates. "
        response_code = 200
    app.logger.info(f"===== PROCESS HOOK: {data_log} =====")
    return message, response_code
