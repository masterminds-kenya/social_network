from flask import Flask
from flask_sqlalchemy import BaseQuery, SQLAlchemy
from sqlalchemy.dialects.mysql import BIGINT
from datetime import datetime as dt
from dateutil import parser
import re
import json

db = SQLAlchemy()


def init_app(app):
    # Disable track modifications, as it unnecessarily uses memory.
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    # app.config['MYSQL_DATABASE_CHARSET'] = 'utf8mb4'
    db.init_app(app)


def from_sql(row):
    """ Translates a SQLAlchemy model instance into a dictionary """
    data = row.__dict__.copy()
    data['id'] = row.id
    # print('============= from_sql ===================')
    # rel = row.__mapper__.relationships
    # all = row.__mapper__
    # print(dir(rel))
    temp = data.pop('_sa_instance_state', None)
    if not temp:
        print('Not a model instance!')
    # TODO: ? Move the cleaning for safe results to this function?
    return data


class GetActive(BaseQuery):
    """ Some models, such as Post, may want to only fetch records not yet processed """
    def get_active(self, not_field=None):
        # if not not_field:
        #     lookup_not_field = {'Post': 'processed', 'Campaign': 'completed'}
        #     curr_class = self.__class__.__name__
        #     not_field = lookup_not_field(curr_class) or None
        return self.query.filter_by(processed=False)


class Brand(db.Model):
    """ Data model for brand accounts. """
    __tablename__ = 'brands'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(47),                 index=True,  unique=True,  nullable=False)
    # company = db.Column(db.String(63),            index=False, unique=False, nullable=False)
    instagram_id = db.Column(BIGINT(unsigned=True), index=True,  unique=True,  nullable=True)
    facebook_id = db.Column(BIGINT(unsigned=True),  index=False, unique=False, nullable=True)
    token = db.Column(db.String(255),               index=False, unique=False, nullable=True)
    token_expires = db.Column(db.DateTime,          index=False, unique=False, nullable=True)
    notes = db.Column(db.String(191),               index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime,               index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,                index=False, unique=False, nullable=False, default=dt.utcnow)
    # # campaigns = backref from Campaign.brands  with lazy='dynamic'
    UNSAFE = {'token', 'token_expires', 'modified', 'created'}

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return '<Brand {}>'.format(self.name)


class User(db.Model):
    """ Data model for user (influencer) accounts.
        Assumes only 1 Instagram per user, and it must be a business account.
        They must have a Facebook Page connected to their business Instagram account.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(47),                 index=True,  unique=True,  nullable=False)
    instagram_id = db.Column(BIGINT(unsigned=True), index=True,  unique=True,  nullable=True)
    facebook_id = db.Column(BIGINT(unsigned=True),  index=False, unique=False, nullable=True)
    token = db.Column(db.String(255),               index=False, unique=False, nullable=True)
    token_expires = db.Column(db.DateTime,          index=False, unique=False, nullable=True)
    notes = db.Column(db.String(191),               index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime,               index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,                index=False, unique=False, nullable=False, default=dt.utcnow)
    insights = db.relationship('Insight',   backref='user', lazy=True, passive_deletes=True)
    audiences = db.relationship('Audience', backref='user', lazy=True, passive_deletes=True)
    posts = db.relationship('Post', query_class=GetActive, backref='user', lazy=True, passive_deletes=True)
    # # campaigns = backref from Campaign.users with lazy='dynamic'
    UNSAFE = {'token', 'token_expires', 'modified', 'created'}

    def __init__(self, *args, **kwargs):
        had_admin = kwargs.pop('admin', None)
        if had_admin:
            print("Source data had an 'admin' parameter that may need to be removed")
        # kwargs['admin'] = True if kwargs.get('admin') == 'on' or kwargs.get('admin') is True else False  # TODO: Possible form injection
        kwargs['facebook_id'] = kwargs.pop('id') if 'facebook_id' not in kwargs and 'id' in kwargs else None
        kwargs['name'] = kwargs.pop('username', kwargs.get('name'))
        if 'token_expires' not in kwargs:
            # making a user from api call
            kwargs['token_expires'] = dt.fromtimestamp(kwargs['token'].get('token_expires')) if 'token' in kwargs and kwargs['token'].get('token_expires') else None
            kwargs['token'] = kwargs['token'].get('access_token') if 'token' in kwargs and kwargs['token'] else None
        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<User {}>'.format(self.name)


class Insight(db.Model):
    """ Data model for insights data on a (influencer's) user's or brands account """
    __tablename__ = 'insights'

    id = db.Column(db.Integer,      primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime,          index=True,  unique=False, nullable=False)
    name = db.Column(db.String(47),            index=True,  unique=True,  nullable=False)
    value = db.Column(db.Integer,              index=False, unique=False, nullable=True)
    # # user = backref from User.insights with lazy='select' (synonym for True)
    metrics = {'impressions', 'reach', 'follower_count'}
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        datestring = kwargs.pop('end_time')
        kwargs['recorded'] = parser.isoparse(datestring)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.user} Insight - {self.name} on {self.recorded}"

    def __repr__(self):
        return '<Insight: {} | User: {} | Date: {} >'.format(self.name, self.user, self.recorded)


class Audience(db.Model):
    """ Data model for current information about the user's audience. """
    # TODO: Refactor to parse out the age groups and gender groups
    __tablename__ = 'audiences'

    id = db.Column(db.Integer,      primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime,          index=True,  unique=False, nullable=False)
    name = db.Column(db.String(47),            index=True,  unique=True,  nullable=False)
    value = db.Column(db.String(47),           index=False, unique=False, nullable=True)
    # # user = backref from User.audiences with lazy='select' (synonym for True)
    metrics = {'audience_city', 'audience_country', 'audience_gender_age'}
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        # TODO: Refactor to avoid the unnecessary kwargs.copy()
        data, kwargs = kwargs.copy(), {}
        kwargs['user_id'] = data.get('user_id')
        kwargs['name'] = re.sub('^audience_', '', data.get('name'))
        kwargs['value'] = json.dumps(data.get('values')[0].get('value'))
        datestring = data.get('values')[0].get('end_time')
        kwargs['recorded'] = parser.isoparse(datestring)
        print(kwargs)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.user} Audience - {self.name} on {self.recorded}"

    def __repr__(self):
        return '<Audience {} | Date: {} >'.format(self.name, self.recorded)


class Post(db.Model):
    """ Instagram media that was posted by an influencer user """
    __tablename__ = 'posts'

    id = db.Column(db.Integer,          primary_key=True)
    user_id = db.Column(db.Integer,     db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True)
    processed = db.Column(db.Boolean, default=False)
    media_id = db.Column(BIGINT(unsigned=True), index=True,  unique=True,  nullable=False)
    media_type = db.Column(db.String(47),       index=False, unique=False, nullable=True)
    caption = db.Column(db.Text,                index=False, unique=False, nullable=True)
    comment_count = db.Column(db.Integer,       index=False, unique=False, nullable=True)
    like_count = db.Column(db.Integer,          index=False, unique=False, nullable=True)
    permalink = db.Column(db.String(191),       index=False, unique=False, nullable=True)
    recorded = db.Column(db.DateTime,           index=False, unique=False, nullable=False)  # timestamp*
    modified = db.Column(db.DateTime,           index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,            index=False, unique=False, nullable=False, default=dt.utcnow)
    # The following 9 are from insights, the first 2 for all kinds of media
    impressions = db.Column(db.Integer,         index=False,  unique=False, nullable=True)
    reach = db.Column(db.Integer,               index=False,  unique=False, nullable=True)
    # The following 3 are for Album and Photo/Video media
    engagement = db.Column(db.Integer,          index=False,  unique=False, nullable=True)
    saved = db.Column(db.Integer,               index=False,  unique=False, nullable=True)
    video_views = db.Column(db.Integer,         index=False,  unique=False, nullable=True)
    # The following 4 are only for stories media
    exits = db.Column(db.Integer,               index=False,  unique=False, nullable=True)
    replies = db.Column(db.Integer,             index=False,  unique=False, nullable=True)
    taps_forward = db.Column(db.Integer,        index=False,  unique=False, nullable=True)
    taps_back = db.Column(db.Integer,           index=False,  unique=False, nullable=True)
    # # user = backref from User.posts with lazy='select' (synonym for True)
    # # campaign = backref from Campaign.posts with lazy='select' (synonym for True)

    metrics = {}
    metrics['basic'] = {'media_type', 'caption', 'like_count', 'permalink', 'timestamp'}  # comment_count requires different permissions
    metrics['insight'] = {'impressions', 'reach'}
    metrics['IMAGE'] = {'engagement', 'saved'}.union(metrics['insight'])
    metrics['VIDEO'] = {'video_views'}.union(metrics['IMAGE'])
    metrics['CAROUSEL_ALBUM'] = {f"carousel_album_{metric}" for metric in metrics['IMAGE']}  # ?in metrics['VIDEO']
    metrics['STORY'] = {'exits', 'replies', 'taps_forward', 'taps_back'}.union(metrics['insight'])
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        datestring = kwargs.pop('timestamp')
        kwargs['recorded'] = parser.isoparse(datestring)
        kwargs['processed'] = True if kwargs.get('processed') in {'on', True} else False
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.user} {self.media_type} Post on {self.recorded}"

    def __repr__(self):
        return '< {} Post | User: {} | Recorded: {} >'.format(self.media_type, self.user, self.recorded)


user_campaign = db.Table(
    'user_campaigns',
    db.Column('id',          db.Integer, primary_key=True),
    db.Column('user_id',     db.Integer, db.ForeignKey('users.id', ondelete="CASCADE")),
    db.Column('campaign_id', db.Integer, db.ForeignKey('campaigns.id', ondelete="CASCADE"))
)

brand_campaign = db.Table(
    'brand_campaigns',
    db.Column('id',          db.Integer, primary_key=True),
    db.Column('brand_id',    db.Integer, db.ForeignKey('brands.id',    ondelete="CASCADE")),
    db.Column('campaign_id', db.Integer, db.ForeignKey('campaigns.id', ondelete="CASCADE"))
)


class Campaign(db.Model):
    """ Relationship between Users and Brands """
    __tablename__ = 'campaigns'

    id = db.Column(db.Integer,       primary_key=True)
    completed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(47),     index=True,  unique=True,  nullable=True)
    notes = db.Column(db.String(191),   index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime,   index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,    index=False, unique=False, nullable=False, default=dt.utcnow)
    users = db.relationship('User', secondary=user_campaign, backref=db.backref('campaigns', lazy='dynamic'))
    brands = db.relationship('Brand', secondary=brand_campaign, backref=db.backref('campaigns', lazy='dynamic'))
    posts = db.relationship('Post', backref='campaign', lazy=True)
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        print('============ Campaign constructor ============')
        print(kwargs)
        # user_id = kwargs.pop('users', None)
        # brand_id = kwargs.pop('brands', None)
        # save related fields
        # print(f"Users: {user_id}, Brands: {brand_id}")
        kwargs['completed'] = True if kwargs.get('completed') in {'on', True} else False
        super().__init__(*args, **kwargs)

    def __str__(self):
        name = self.name if self.name else self.id
        brands = ', '.join([brand.name for brand in self.brands]) if self.brands else ['NA']
        return f"Campaign: {name} with Brand(s): {brands}"

    def __repr__(self):
        name = self.name if self.name else self.id
        brands = ', '.join([brand.name for brand in self.brands]) if self.brands else ['NA']
        return '<Campaign: {} | Brands: {} >'.format(name, brands)


def create_many(dataset, Model=User):
    all_results = []
    for data in dataset:
        model = Model(**data)
        db.session.add(model)
        all_results.append(from_sql(model))
        # all_results.append((model))  # This might be identical as above since id not assigned yet
        # safe_results = {k: results[k] for k in results.keys() - Model.UNSAFE}
    # TODO: ? Refactor to use db.session.add_all() ?
    db.session.commit()
    # TODO: List comprehension to return the array of dictionaries to include the model id.
    # all_results = [from_sql(ea) for ea in all_results]
    return all_results


def create(data, Model=User):
    from pprint import pprint
    # TODO: Refactor to work as many or one: check if we have a list of obj, or single obj
    # dataset = [data] if not isinstance(data, list) else data
    # then use code written in create_many for this dataset
    print('--------- Inspecting the create function -------------')
    pprint(data)
    model = Model(**data)
    print('-------First was data, now model ----------------------------------')
    pprint(model)
    db.session.add(model)
    db.session.commit()
    results = from_sql(model)
    print('----------model after commit() -------------------------------')
    pprint(model)
    print('--------results before safe ---------------------------------')
    pprint(results)
    # TODO: Refactor safe_results for when we create many
    safe_results = {k: results[k] for k in results.keys() - Model.UNSAFE}
    # TODO: Return a single obj if we created only one?
    print('---------safe results --------------------------------')
    pprint(safe_results)
    return safe_results


def read(id, Model=User, safe=True):
    model = Model.query.get(id)
    if not model:
        return None
    results = from_sql(model)
    safe_results = {k: results[k] for k in results.keys() - Model.UNSAFE}
    output = safe_results if safe else results
    if Model == User:
        # TODO: Is the following something we want? Corpse code?
        # ?Find min and max of dates for each Insight.metrics?
        # output['insight'] = [{name: '', min: '', max: ''}, ...]
        # insights = [from_sql(ea) for ea in model.insights]
        # hold = {key: [] for key in Insight.metrics}
        # print('Hold: ', hold)
        # print('=======================================')
        # [hold[ea['name']].append(ea) for ea in insights if ea['name'] in Insight.metrics]
        # output['insight'] = hold
        # # output['insight'] = [from_sql(ea) for ea in model.insights]
        if len(model.insights) > 0:
            output['insight'] = True
        if len(model.audiences) > 0:
            output['audience'] = [from_sql(ea) for ea in model.audiences]
    return output


def update(data, id, Model=User):
    # Any checkbox field should have been prepared by process_form()
    model = Model.query.get(id)
    for k, v in data.items():
        setattr(model, k, v)
    db.session.commit()
    results = from_sql(model)
    safe_results = {k: results[k] for k in results.keys() - Model.UNSAFE}
    return safe_results


def delete(id, Model=User):
    Model.query.filter_by(id=id).delete()
    db.session.commit()


def all(Model=User):
    sort_field = Model.name if hasattr(Model, 'name') else Model.id
    query = (Model.query.order_by(sort_field))
    models = query.all()
    return models


def _create_database():
    """ Currently only works if we do not need to drop the tables before creating them """
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    init_app(app)
    with app.app_context():
        # db.drop_all()
        # print("All tables dropped!")
        db.create_all()
    print("All tables created")


if __name__ == '__main__':
    _create_database()
