from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime as dt
from dateutil import parser
import re
import json

db = SQLAlchemy()


def init_app(app):
    # Disable track modifications, as it unnecessarily uses memory.
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    db.init_app(app)


def from_sql(row):
    """ Translates a SQLAlchemy model instance into a dictionary """
    data = row.__dict__.copy()
    data['id'] = row.id
    data.pop('_sa_instance_state')
    return data


class Brand(db.Model):
    """ Data model for brand accounts. """
    __tablename__ = 'brands'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63),         index=True,  unique=True,  nullable=False)
    # company = db.Column(db.String(63),      index=False, unique=False, nullable=False)
    facebook_id = db.Column(db.Integer,     index=False,  unique=False,  nullable=True)
    token = db.Column(db.String(255),       index=False, unique=False, nullable=True)
    token_expires = db.Column(db.DateTime,  index=False, unique=False, nullable=True)
    notes = db.Column(db.Text,              index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime,       index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,        index=False, unique=False, nullable=False, default=dt.utcnow)
    # users = db.relationship('Campaign', back_populates='brand')
    # # users = db.relationship('User', secondary='campaigns')
    UNSAFE = {'facebook_id', 'token', 'token_expires', 'modified', 'created'}

    def __str__(self):
        return f"{self.name} Brand"

    def __repr__(self):
        return '<Brand {}>'.format(self.name)


class User(db.Model):
    """ Data model for user (influencer) accounts.
        Assumes only 1 Instagram per user, and it must be a business account.
        They must have a Facebook Page connected to their business Instagram account.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63),         index=False, unique=True,  nullable=False)
    instagram_id = db.Column(db.String(63), index=True,  unique=True,  nullable=True)
    facebook_id = db.Column(db.String(63),  index=True,  unique=False,  nullable=True)
    token = db.Column(db.String(255),       index=False, unique=False, nullable=True)
    token_expires = db.Column(db.DateTime,  index=False, unique=False, nullable=True)
    notes = db.Column(db.Text,              index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime,       index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,        index=False, unique=False, nullable=False, default=dt.utcnow)
    insights = db.relationship('Insight', backref='user', lazy=True, passive_deletes=True)
    audiences = db.relationship('Audience', backref='user', lazy=True, passive_deletes=True)
    posts = db.relationship('Post', backref='user', lazy=True, passive_deletes=True)
    # brands = db.relationship('Campaign', back_populates='user')
    # # brands = db.relationship('Brand', secondary='campaigns')
    UNSAFE = {'token', 'token_expires', 'facebook_id', 'modified', 'created'}

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

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime,          index=True,  unique=False, nullable=False)
    name = db.Column(db.String(255),           index=True, unique=False, nullable=False)
    value = db.Column(db.Text,                 index=False, unique=False, nullable=True)
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
    __tablename__ = 'audiences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime,          index=True,  unique=False, nullable=False)
    name = db.Column(db.String(255),           index=True, unique=False, nullable=False)
    value = db.Column(db.Text,                 index=False, unique=False, nullable=True)
    metrics = {'audience_city', 'audience_country', 'audience_gender_age'}
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
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

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True)
    processed = db.Column(db.Boolean, default=False)
    media_id = db.Column(db.Integer,      index=True,   unique=True,  nullable=False)
    media_type = db.Column(db.String(64), index=False,   unique=False, nullable=True)
    caption = db.Column(db.Text,          index=False,  unique=False, nullable=True)
    comment_count = db.Column(db.Integer, index=False,  unique=False, nullable=True)
    like_count = db.Column(db.Integer,    index=False,  unique=False, nullable=True)
    permalink = db.Column(db.String(255), index=False,  unique=False, nullable=True)
    recorded = db.Column(db.DateTime,     index=False,  unique=False, nullable=False)  # timestamp*
    modified = db.Column(db.DateTime,       index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,        index=False, unique=False, nullable=False, default=dt.utcnow)
    # The following 9 are from insights, the first 2 for all kinds of media
    impressions = db.Column(db.Integer,   index=False,  unique=False, nullable=True)
    reach = db.Column(db.Integer,         index=False,  unique=False, nullable=True)
    # The following 3 are for Album and Photo/Video media
    engagement = db.Column(db.Integer,    index=False,  unique=False, nullable=True)
    saved = db.Column(db.Integer,         index=False,  unique=False, nullable=True)
    video_views = db.Column(db.Integer,   index=False,  unique=False, nullable=True)
    # The following 4 are only for stories media
    exits = db.Column(db.Integer,         index=False,  unique=False, nullable=True)
    replies = db.Column(db.Integer,       index=False,  unique=False, nullable=True)
    taps_forward = db.Column(db.Integer,  index=False,  unique=False, nullable=True)
    taps_back = db.Column(db.Integer,     index=False,  unique=False, nullable=True)

    # instagram_id = db.Column(db.String(80),    index=True,  unique=True,  nullable=False)  # IG indentity
    basic_metrics = {'media_type', 'caption', 'like_count', 'permalink', 'timestamp'}  # comment_count requires different permissions
    insight_metrics = {'impressions', 'reach'}
    media_metrics = {'engagement', 'saved', 'video_views'}.union(insight_metrics)
    album_metrics = {f"carousel_album_{metric}" for metric in media_metrics}
    story_metrics = {'exits', 'replies', 'taps_forward', 'taps_back'}.union(insight_metrics)
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        datestring = kwargs.pop('timestamp')
        kwargs['recorded'] = parser.isoparse(datestring)
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return '<Post: L {}, C {} | Date: {} | Recorded: {} >'.format(self.like_count, self.comment_count, self.timestamp, self.recorded)


user_campaign = db.Table(
    'user_campaigns',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete="CASCADE")),
    db.Column('campaign_id', db.Integer, db.ForeignKey('campaigns.id', ondelete="CASCADE"))
)

brand_campaign = db.Table(
    'brand_campaigns',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('brand_id', db.Integer, db.ForeignKey('brands.id', ondelete="CASCADE")),
    db.Column('campaign_id', db.Integer, db.ForeignKey('campaigns.id', ondelete="CASCADE"))
)


class Campaign(db.Model):
    """ Relationship between Users and Brands """
    __tablename__ = 'campaigns'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=False)
    notes = db.Column(db.Text,              index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime,       index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,        index=False, unique=False, nullable=False, default=dt.utcnow)
    # start_date = db.Column(db.DateTime,     index=False, unique=False, nullable=False, default=dt.utcnow)
    # end_date = db.Column(db.DateTime,       index=False, unique=False, nullable=True)
    users = db.relationship('User', secondary=user_campaign, backref=db.backref('campaigns'))
    brand = db.relationship('Brand', secondary=brand_campaign, backref=db.backref('campaigns'))
    posts = db.relationship('Post', backref='campaign', lazy=True)
    UNSAFE = {''}

    def __repr__(self):
        return '<Campaign {} | Brand: {} | Starts: {}>'.format(self.id, self.brand_id, self.start_date)


def create_many(dataset, Model=User):
    all_results = []
    for data in dataset:
        model = Model(**data)
        db.session.add(model)
        all_results.append(from_sql(model))
        # all_results.append((model))  # This might be identical as above since id not assigned yet
        # safe_results = {k: results[k] for k in results.keys() - Model.UNSAFE}
    db.session.commit()
    # TODO: List comprehension to return the array of dictionaries to include the model id.
    # all_results = [from_sql(ea) for ea in all_results]
    return all_results


def create(data, Model=User):
    # TODO: Refactor to work as many or one: check if we have a list of obj, or single obj
    # dataset = [data] if not isinstance(data, list) else data
    # then use code written in create_many for this dataset
    model = Model(**data)
    db.session.add(model)
    db.session.commit()
    results = from_sql(model)
    # TODO: Refactor safe_results for when we create many
    safe_results = {k: results[k] for k in results.keys() - Model.UNSAFE}
    # TODO: Return a single obj if we created only one?
    return safe_results


def read(id, Model=User, safe=True):
    model = Model.query.get(id)
    if not model:
        return None
    results = from_sql(model)
    safe_results = {k: results[k] for k in results.keys() - Model.UNSAFE}
    output = safe_results if safe else results
    if Model == User:
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
    # Any checkbox field will need to be modified.
    if Model == User:
        # data['admin'] = True if 'admin' in data and data['admin'] == 'on' else False
        pass
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
    sort_field = Model.name if Model in {User, Brand} else Model.id
    query = (Model.query.order_by(sort_field))
    models = query.all()
    return models


def _create_database():
    """ Currently only works if we do not need to drop the tables before creating them """
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    init_app(app)
    with app.app_context():
        db.drop_all()
        print("All tables dropped!")
        db.create_all()
    print("All tables created")


if __name__ == '__main__':
    _create_database()
