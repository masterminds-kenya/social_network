from .model_db import db, from_sql, User, Post, Audience, Campaign
import json


def update_campaign(ver, request):
    """ Handle adding or removing posts assigned to a campaign, as well removing posts from the processing cue. """
    form_dict = request.form.to_dict(flat=True)
    # Radio Button | Management | Results | Manage Outcome  | Result Outcome
    # accept       |  data.id   |    0    | camp_id = val   | leave alone
    # reject       |    -1      |   -1    | processed       | camp_id = None
    # ignore       |     0      |   -2    | leave alone     | unset process & camp_id
    try:
        data = {int(key.replace('assign_', '')): int(val) for (key, val) in form_dict.items() if val != '0'}
    except ValueError as e:
        # TODO: handle error
        return False
    modified = Post.query.filter(Post.id.in_(data.keys())).all()
    for post in modified:
        campaign_id = data[post.id]
        print(campaign_id)
        campaign = Campaign.query.get(campaign_id)
        print(campaign)
        # post.processed = True if data[post.id] != -2 else False  # old
        if data[post.id] != -2:
            campaign.posts.append(post)
            print(f"Add {post} to Campaign with id {campaign_id} ")
        elif post in campaign.posts:
            print(f"Remove {post} from Campaign with id {campaign_id} ")
            campaign.posts.remove(post)
        # post.campaign_id = data[post.id] if data[post.id] > 0 else None  # old
        if data[post.id] > 0:
            print(f"Reject {post} for Campaign with id {campaign_id} ")
            campaign.rejected.append(post)
        else:
            print(f"Let {post} back as unprocessed candidate for Campaign with id {campaign_id} ")
            campaign.rejected.remove(post)
    try:
        db.session.commit()
    except Exception as e:
        print("We had an exception on the campaign update commit")
        print(e)
        # TODO: handle exception
        return False
    return True


def post_display(post):
    """ Since different media post types have different metrics, we only want to show the appropriate fields. """
    Model = Post
    if isinstance(post, Model):
        post = from_sql(post, related=False, safe=True)
    fields = {'id', 'user_id', 'campaign_id', 'processed', 'recorded'}
    fields.update(Model.metrics['basic'])
    fields.discard('timestamp')
    fields.update(Model.metrics[post['media_type']])
    return {key: val for (key, val) in post.items() if key in fields}


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
    bool_fields = {'campaign': 'completed', 'post': 'processed', 'login': 'remember'}
    # TODO: Add logic to find all Boolean fields in models and handle appropriately.
    if mod in bool_fields:
        data[bool_fields[mod]] = True if data.get(bool_fields[mod]) in {'on', True} else False
    return data
