from .model_db import db, User, Post, Audience
from flask import current_app as app
import json


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
        # TODO: handle error
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
        app.logger.error("We had an exception on the campaign update commit")
        app.logger.error(e)
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
    if mod in ['login', *User.roles]:
        data['role'] = data.get('role', mod)
        # checking, or creating, password hash is handled outside of this function.
        # On User edit, keep the current password if they left the input box blank.
        if not data.get('password'):
            data.pop('password', None)
        # Create IG media_count & followers_count here, then they are associated on User create or update.
        models = []
        for name in Audience.ig_data:  # {'media_count', 'followers_count'}
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
