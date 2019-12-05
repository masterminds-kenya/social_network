from .model_db import db, from_sql, Brand, User, Post


def update_campaign(ver, request):
    form_dict = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
    # Radio Button | Management | Results | Manage Outcome  | Result Outcome
    # accept       |  data.id   |    0    | camp_id = val   | leave alone
    # reject       |    -1      |   -1    | processed       | camp_id = None
    # ignore       |     0      |   -2    | leave alone     | unset process & camp_id
    try:
        data = {int(key.replace('assign_', '')): int(val) for (key, val) in form_dict.items() if val != '0'}
    except ValueError as e:
        # handle error
        return False
    modified = Post.query.filter(Post.id.in_(data.keys())).all()
    for post in modified:
        post.processed = True if data[post.id] != -2 else False
        post.campaign_id = data[post.id] if data[post.id] > 0 else None
    try:
        db.session.commit()
    except Exception as e:
        # handle exception
        return False
    return True


def post_display(post):
    Model = Post
    if isinstance(post, Model):
        post = from_sql(post)
    fields = {'id', 'user_id', 'campaign_id', 'processed', 'recorded'}
    fields.update(Model.metrics['basic'])
    fields.discard('timestamp')
    fields.update(Model.metrics[post['media_type']])
    model = {key: val for (key, val) in post.items() if key in fields}
    # model = {key: model[key] for key in fields}
    return model


def process_form(mod, request):
    # If Model has relationship collections set in form, then we must capture these before flattening the input
    # I believe this is only needed for campaigns.
    save = {}
    if mod == 'campaign':
        data = request.form.to_dict(flat=False)  # TODO: add better form validate method for security.
        # capture the relationship collections
        # TODO: I might be missing how SQLAlchemy intends for use to handle related models
        # the following may not be needed, or need to be managed differently
        rel_collections = (('brands', Brand), ('users', User), ('posts', Post))
        for rel, Model in rel_collections:
            if rel in data:
                model_ids = [int(ea) for ea in data[rel]]
                models = Model.query.filter(Model.id.in_(model_ids)).all()
                save[rel] = models
    data = request.form.to_dict(flat=True)  # TODO: add form validate method for security.
    data.update(save)  # adds to the data dict if we did save some relationship collections
    # If the form has a checkbox for a Boolean in the form, we may need to reformat.
    # currently I think only Campaign and Post have checkboxes
    bool_fields = {'campaign': 'completed', 'post': 'processed'}
    # TODO: Add logic to find all Boolean fields in models and handle appropriately.
    if mod in bool_fields:
        data[bool_fields[mod]] = True if data.get(bool_fields[mod]) in {'on', True} else False
    return data
