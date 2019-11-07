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
    name = db.Column(db.String(64),         index=True,  unique=True,  nullable=False)
    # company = db.Column(db.String(64),      index=False, unique=False, nullable=False)
    facebook_id = db.Column(db.String(80),  index=True,  unique=True,  nullable=True)
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
    name = db.Column(db.String(64),         index=False, unique=True,  nullable=False)
    email = db.Column(db.String(80),        index=True,  unique=True,  nullable=False)
    token = db.Column(db.String(255),       index=False, unique=False, nullable=True)
    token_expires = db.Column(db.DateTime,  index=False, unique=False, nullable=True)
    facebook_id = db.Column(db.String(80),  index=True,  unique=True,  nullable=True)
    instagram_id = db.Column(db.String(80), index=True,  unique=True,  nullable=True)
    notes = db.Column(db.Text,              index=False, unique=False, nullable=True)
    admin = db.Column(db.Boolean,           index=False, unique=False, nullable=False)
    modified = db.Column(db.DateTime,       index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,        index=False, unique=False, nullable=False, default=dt.utcnow)
    insights = db.relationship('Insight', backref='user', lazy=True, passive_deletes=True)
    audiences = db.relationship('Audience', backref='user', lazy=True, passive_deletes=True)
    # posts = db.relationship('Post', backref='user', lazy=True)
    # brands = db.relationship('Campaign', back_populates='user')
    # # brands = db.relationship('Brand', secondary='campaigns')
    UNSAFE = {'token', 'token_expires', 'facebook_id', 'modified', 'created'}

    def __init__(self, *args, **kwargs):
        kwargs['admin'] = True if 'admin' in kwargs and kwargs['admin'] == 'on' else False  # TODO: Possible form injection
        kwargs['facebook_id'] = kwargs.pop('id') if 'id' in kwargs else None
        # kwargs['token_expires'] = dt.fromtimestamp(kwargs['token'].get('token_expires')) if 'token' in kwargs and kwargs['token'].get('token_expires') else None
        # kwargs['token'] = kwargs['token'].get('access_token') if 'token' in kwargs and kwargs['token'] else None
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

# class Post(db.Model):
#     """ Instagram posts (media) by an influencer (user) """
#     __tablename__ = 'posts'

#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
#     ig_id = db.Column(db.String(80),    index=True,  unique=True,  nullable=False)  # IG indentity
#     recorded = db.Column(db.DateTime,   index=True,  unique=False, nullable=False)  # timestamp*
#     likes = db.Column(db.Integer,       index=True,  unique=False, nullable=False)
#     count_comm = db.Column(db.Integer,  index=True,  unique=False, nullable=False)
#     comments = db.Column(db.text,       index=False, unique=False, nullable=True)

#     def __repr__(self):
#         return '<Post: L {}, C {} | Date: {} >'.format(self.likes, self.count_comm, self.recorded)


# class Campaign(db.Model):
#     """ Relationship between User and Brand """
#     __tablename__ = 'campaigns'

#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'), nullable=False)
#     # input fields for insight data here
#     notes = db.Column(db.Text,              index=False, unique=False, nullable=True)
#     modified = db.Column(db.DateTime,       index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
#     created = db.Column(db.DateTime,        index=False, unique=False, nullable=False, default=dt.utcnow)
#     start_date = db.Column(db.DateTime,     index=False, unique=False, nullable=False, default=dt.utcnow)
#     end_date = db.Column(db.DateTime,       index=False, unique=False, nullable=True)
#     user = db.relationship('User', back_populates='brands')
#     brand = db.relationship('Brand', back_populates='users')
#     # user = db.relationship(User, backref=db.backref('campaigns'))
#     # product = db.relationship(Brand, backref=db.backref('campaigns'))

#     def __repr__(self):
#         return '<Campaign {} | Brand: {} | Starts: {}>'.format(self.id, self.brand_id, self.start_date)


def create_many(dataset, Model=User):
    all_results = []
    for data in dataset:
        model = Model(**data)
        db.session.add(model)
        all_results.append(from_sql(model))
        # safe_results = {k: results[k] for k in results.keys() - Model.UNSAFE}
    db.session.commit()
    return all_results


def create(data, Model=User):
    model = Model(**data)
    db.session.add(model)
    db.session.commit()
    results = from_sql(model)
    safe_results = {k: results[k] for k in results.keys() - Model.UNSAFE}
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
    if Model == User:
        data['admin'] = True if 'admin' in data and data['admin'] == 'on' else False
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
        # db.drop_all()
        # print("All tables dropped!")
        db.create_all()
    print("All tables created")


if __name__ == '__main__':
    _create_database()
