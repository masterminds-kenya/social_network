from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime as dt

db = SQLAlchemy()


def init_app(app):
    # Disable track modifications, as it unnecessarily uses memory.
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    db.init_app(app)


def from_sql(row):
    """Translates a SQLAlchemy model instance into a dictionary"""
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
    insights = db.relationship('Insight', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)
    # brands = db.relationship('Campaign', back_populates='user')
    # # brands = db.relationship('Brand', secondary='campaigns')
    UNSAFE = {'token', 'token_expires', 'facebook_id', 'modified', 'created'}

    def __repr__(self):
        return '<User {}>'.format(self.name)


class Insight(db.Model):
    """ Data model for insights data on a (influencer's) user's or brand's account """
    __tablename__ = 'insights'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recorded = db.Column(db.DateTime,         index=True,  unique=False, nullable=False)
    old_impressions = db.Column(db.Integer,   index=True,  unique=False, nullable=False)
    new_impressions = db.Column(db.Integer,   index=True,  unique=False, nullable=False)
    old_reach = db.Column(db.Integer,         index=True,  unique=False, nullable=False)
    new_reach = db.Column(db.Integer,         index=True,  unique=False, nullable=False)
    old_profile_views = db.Column(db.Integer, index=True,  unique=False, nullable=False)
    new_profile_views = db.Column(db.Integer, index=True,  unique=False, nullable=False)

    def __repr__(self):
        impressions = self.new_impressions - self.old_impressions
        reach = self.new_reach - self.old_reach
        p_views = self.new_profile_views - self.old_profile_views
        return '<Insight {}, {}, {} | Date: {} >'.format(impressions, reach, p_views, self.recorded)


class Post(db.Model):
    """ Instagram posts (media) by an influencer (user) """
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ig_id = db.Column(db.String(80),    index=True,  unique=True,  nullable=False)  # IG indentity
    recorded = db.Column(db.DateTime,   index=True,  unique=False, nullable=False)  # timestamp*
    likes = db.Column(db.Integer,       index=True,  unique=False, nullable=False)
    count_comm = db.Column(db.Integer,  index=True,  unique=False, nullable=False)
    comments = db.Column(db.text,       index=False, unique=False, nullable=True)

    def __repr__(self):
        return '<Post: L {}, C {} | Date: {} >'.format(self.likes, self.count_comm, self.recorded)


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


def create(data, Model=User):
    # data['created'], data['modified'] = dt.now(), dt.now()
    if Model == User:
        data['admin'] = True if 'admin' in data and data['admin'] == 'on' else False  # TODO: Possible form injection
        data['facebook_id'] = data.pop('id') if 'id' in data else None
        data['token_expires'] = dt.fromtimestamp(data['token_expires']) if 'token_expires' in data and data['token_expires'] else None
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
    return output


def update(data, id, Model=User):
    # data['modified'] = dt.now()
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


def list(Model=User):
    query = (Model.query.order_by(Model.name))
    models = query.all()
    return models


def _create_database():
    """ If this script is run directly, first we drop and then create
    all the tables necessary to run the application.
    """
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    init_app(app)
    with app.app_context():
        db.drop_all()
        db.create_all()
    print("All tables created")


if __name__ == '__main__':
    _create_database()
