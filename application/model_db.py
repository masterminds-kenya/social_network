from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# from flask_sqlalchemy import BaseQuery, SQLAlchemy  # if we create custom query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy import or_
from datetime import datetime as dt
from dateutil import parser
import re
import json
from pprint import pprint  # only for debugging
# TODO: see "Setting up Constraints when using the Declarative ORM Extension" at https://docs.sqlalchemy.org/en/13/core/constraints.html#unique-constraint

db = SQLAlchemy()


def fix_date(Model, data):
    datestring = ''
    if Model == Insight:
        datestring = data.pop('end_time', None)
    elif Model == Audience:
        datestring = data.get('values', [{}])[0].get('end_time')  # TODO: Are we okay assuming 'end_time' is same for all in this array of responses?
    elif Model == Post:
        datestring = data.pop('timestamp', None)
    data['recorded'] = parser.isoparse(datestring).replace(tzinfo=None) if datestring else data.get('recorded')
    return data


def init_app(app):
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)  # Disabled since it unnecessary uses memory
    # app.config.setdefault('SQLALCHEMY_ECHO', True)  # Turns on A LOT of logging.
    # app.config['MYSQL_DATABASE_CHARSET'] = 'utf8mb4'  # Perhaps already set by default in MySQL
    db.init_app(app)


def from_sql(row, related=False, safe=False):
    """ Translates a SQLAlchemy model instance into a dictionary """
    data = row.__dict__.copy()
    data['id'] = row.id
    print('============= from_sql ===================')
    print(row.__class__)
    if related:
        rel = row.__mapper__.relationships
        print(rel)
        # print(dir(rel))
    temp = data.pop('_sa_instance_state', None)
    if not temp:
        print('Not a model instance!')
    if safe:
        Model = row.__class__
        data = {k: data[k] for k in data.keys() - Model.UNSAFE}

    # TODO: ? Move the cleaning for safe results to this function?
    return data


# class GetActive(BaseQuery):
#     """ Some models, such as Post, may want to only fetch records not yet processed """
#     def get_active(self, not_field=None):
#         # if not not_field:
#         #     lookup_not_field = {'Post': 'processed', 'Campaign': 'completed'}
#         #     curr_class = self.__class__.__name__
#         #     not_field = lookup_not_field(curr_class) or None
#         return self.query.filter_by(processed=False)


class Brand(db.Model):
    """ Data model for brand accounts. """
    __tablename__ = 'brands'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(47),                 index=True,  unique=True,  nullable=False)
    instagram_id = db.Column(BIGINT(unsigned=True), index=True,  unique=True,  nullable=True)
    facebook_id = db.Column(BIGINT(unsigned=True),  index=False, unique=False, nullable=True)
    token = db.Column(db.String(255),               index=False, unique=False, nullable=True)
    token_expires = db.Column(db.DateTime,          index=False, unique=False, nullable=True)
    notes = db.Column(db.String(191),               index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime,               index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,                index=False, unique=False, nullable=False, default=dt.utcnow)
    # # campaigns = backref from Campaign.brands  with lazy='dynamic'
    UNSAFE = {'token', 'token_expires', 'modified', 'created'}

    def __init__(self, *args, **kwargs):
        kwargs['facebook_id'] = kwargs.pop('id') if 'facebook_id' not in kwargs and 'id' in kwargs else None
        kwargs['name'] = kwargs.pop('username', kwargs.get('name'))
        if 'token_expires' not in kwargs and 'token' in kwargs:
            # modifications for parsing data from api call
            token_expires = kwargs['token'].get('token_expires', None)
            kwargs['token_expires'] = dt.fromtimestamp(token_expires) if token_expires else None
            kwargs['token'] = kwargs['token'].get('access_token', None)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return '<Brand {}>'.format(self.name)


class User(db.Model):
    """ Data model for user (influencer) accounts.
        Assumes only 1 Instagram per user, and it must be a business account.
        They must have a Facebook Page connected to their business Instagram account.
    """
    # TYPES = [
    #     ('influencer', 'Influencer'),
    #     ('brand', 'Brand')
    # ]
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(47),                 index=False, unique=False, nullable=True)
    # account = db.Column(db.ChoiceType(TYPES))
    instagram_id = db.Column(BIGINT(unsigned=True), index=True,  unique=True,  nullable=True)
    facebook_id = db.Column(BIGINT(unsigned=True),  index=False, unique=False, nullable=True)
    token = db.Column(db.String(255),               index=False, unique=False, nullable=True)
    token_expires = db.Column(db.DateTime,          index=False, unique=False, nullable=True)
    notes = db.Column(db.String(191),               index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime,               index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,                index=False, unique=False, nullable=False, default=dt.utcnow)
    insights = db.relationship('Insight',   backref='user', lazy=True, passive_deletes=True)
    audiences = db.relationship('Audience', backref='user', lazy=True, passive_deletes=True)
    posts = db.relationship('Post', backref='user', lazy=True, passive_deletes=True)  # ? query_class=GetActive,
    # # campaigns = backref from Campaign.users with lazy='dynamic'
    UNSAFE = {'token', 'token_expires', 'modified', 'created'}

    def __init__(self, *args, **kwargs):
        kwargs['facebook_id'] = kwargs.pop('id') if 'facebook_id' not in kwargs and 'id' in kwargs else None
        kwargs['name'] = kwargs.pop('username', kwargs.get('name'))
        if 'token_expires' not in kwargs and 'token' in kwargs:
            # modifications for parsing data from api call
            token_expires = kwargs['token'].get('token_expires', None)
            kwargs['token_expires'] = dt.fromtimestamp(token_expires) if token_expires else None
            kwargs['token'] = kwargs['token'].get('access_token', None)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<User {}>'.format(self.name)


class Insight(db.Model):
    """ Data model for insights data on a (influencer's) user's or brands account """
    __tablename__ = 'insights'
    __table_args__ = (db.UniqueConstraint('user_id', 'recorded', 'name', name='uq_insights_recorded_name'),)

    id = db.Column(db.Integer,      primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime,          index=False, unique=False, nullable=False)
    name = db.Column(db.String(47),            index=False, unique=False, nullable=False)
    value = db.Column(db.Integer,              index=False, unique=False, nullable=True)
    # # user = backref from User.insights with lazy='select' (synonym for True)
    metrics = {'impressions', 'reach', 'follower_count'}
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        kwargs = fix_date(Insight, kwargs)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.user} Insight - {self.name} on {self.recorded}"

    def __repr__(self):
        return '<Insight: {} | User: {} | Date: {} >'.format(self.name, self.user, self.recorded)


class Audience(db.Model):
    """ Data model for current information about the user's audience. """
    # TODO: If this data not taken over by Neo4j, then refactor to parse out the age groups and gender groups
    __tablename__ = 'audiences'
    __table_args__ = (db.UniqueConstraint('user_id', 'recorded', 'name', name='uq_audiences_recorded_name'),)

    id = db.Column(db.Integer,      primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime,          index=False, unique=False, nullable=False)
    name = db.Column(db.String(47),            index=False, unique=False, nullable=False)
    value = db.Column(db.Text,                 index=False, unique=False, nullable=True)
    # # user = backref from User.audiences with lazy='select' (synonym for True)
    metrics = {'audience_city', 'audience_country', 'audience_gender_age'}
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        kwargs = fix_date(Audience, kwargs)
        data, kwargs = kwargs.copy(), {}  # cleans out the not-needed data from API call
        kwargs['recorded'] = data.get('recorded')
        kwargs['user_id'] = data.get('user_id')
        kwargs['name'] = re.sub('^audience_', '', data.get('name'))
        kwargs['value'] = data.get('value', json.dumps(data.get('values', [{}])[0].get('value')))
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
    comments_count = db.Column(db.Integer,      index=False, unique=False, nullable=True)
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
    metrics['basic'] = {'media_type', 'caption', 'comments_count', 'like_count', 'permalink', 'timestamp'}
    metrics['insight'] = {'impressions', 'reach'}
    metrics['IMAGE'] = {'engagement', 'saved'}.union(metrics['insight'])
    metrics['VIDEO'] = {'video_views'}.union(metrics['IMAGE'])
    metrics['CAROUSEL_ALBUM'] = {f"carousel_album_{metric}" for metric in metrics['IMAGE']}  # ?in metrics['VIDEO']
    metrics['STORY'] = {'exits', 'replies', 'taps_forward', 'taps_back'}.union(metrics['insight'])
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        kwargs = fix_date(Post, kwargs)
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


def create(data, Model=User):
    try:
        model = Model(**data)
        db.session.add(model)
        db.session.commit()
    except IntegrityError as error:
        # most likely only happening on Brand, User, or Campaign
        print('----------- IntegrityError Condition -------------------')
        pprint(error)
        db.session.rollback()
        columns = Model.__table__.columns
        unique = {c.name: data.get(c.name) for c in columns if c.unique}
        pprint(unique)
        model = Model.query.filter(*[getattr(Model, key) == val for key, val in unique.items()]).one_or_none()
        if model:
            print(f'----- Instead of Create, we are using existing record with id: {model.id} -----')
        else:
            print(f'----- Cannot create due to collision on unique fields. Cannot retrieve existing record')
    # except Exception as e:
    #     print('**************** DB CREATE Error *******************')
    #     print(e)
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


def create_many(dataset, Model=User):
    """ Currently only used for temporary developer_admin function """
    all_results = []
    for data in dataset:
        model = Model(**data)
        db.session.add(model)
        all_results.append(model)
    db.session.commit()
    return [from_sql(ea) for ea in all_results]


def create_or_update_many(dataset, user_id=None, Model=Post):
    """ Create or Update if the record exists for all of the dataset list """
    # print(f'============== Create or Update Many {Model.__name__} ====================')
    allowed_models = {Post, Insight, Audience}
    if Model not in allowed_models:
        return []
    composite_unique = ['recorded', 'name'] if Model in {Insight, Audience} else False
    # Note: initially all Models only had 1 non-pk unique field, except for unused Brand instagram_id field.
    # However, both the Insight and Audience models have a composite unique requirement (user_id, recorded, name)
    # insp = db.inspect(Model)
    all_results, add_count, update_count, error_set = [], 0, 0, []
    # print(f'---- Initial dataset has {len(dataset)} records ----')
    if composite_unique:
        q = Model.query.filter(user_id == user_id) if user_id else Model.query()
        match = q.all()
        # print(f'------ Composite Unique for {Model.__name__}: {len(match)} possible matches ----------------')
        lookup = {tuple([getattr(ea, key) for key in composite_unique]): ea for ea in match}
        # pprint(lookup)
        for data in dataset:
            data = fix_date(Model, data)  # fix incoming data 'recorded' as needed for this Model
            # TODO: The following patch for Audience is not needed once we improve API validation process
            if Model == Audience:
                data['name'] = re.sub('^audience_', '', data.get('name'))
                data['value'] = json.dumps(data.get('values', [{}])[0].get('value'))
                data.pop('id', None)
            key = tuple([data.get(ea) for ea in composite_unique])
            model = lookup.get(key, None)
            # print(f'------- {key} -------')
            if model:
                # pprint(model)
                [setattr(model, k, v) for k, v in data.items()]
                update_count += 1
            else:
                # print('No match in existing data')
                model = Model(**data)
                db.session.add(model)
                add_count += 1
            all_results.append(model)
    else:
        # The following should work with multiple single column unique fields, but no composite unique requirements
        # print('----------------- Unique Columns -----------------------')  # TODO: remove
        columns = Model.__table__.columns
        unique = {c.name: [] for c in columns if c.unique}
        [unique[key].append(val) for ea in dataset for (key, val) in ea.items() if key in unique]
        # pprint(unique)
        # unique now has a key for each unique field, and a list of all the values that we want to assign those fields from the dataset
        q_to_update = Model.query.filter(or_(*[getattr(Model, key).in_(arr) for key, arr in unique.items()]))
        match = q_to_update.all()
        # match is a list of current DB records that have a unique field with a value matching the incoming dataset
        # print(f'---- There seems to be {len(match)} records to update ----')
        match_dict = {}
        for key in unique.keys():
            lookup_record_by_val = {getattr(ea, key): ea for ea in match}
            match_dict[key] = lookup_record_by_val
        for data in dataset:
            # find all records in match that would collide with the values of this data
            updates = [lookup[int(data[unikey])] for unikey, lookup in match_dict.items() if int(data[unikey]) in lookup]
            if len(updates) > 0:
                if len(updates) == 1:
                    model = updates[0]
                    for k, v in data.items():
                        setattr(model, k, v)
                    update_count += 1
                    all_results.append(model)
                else:
                    # print('------- Got a Multiple Match Record ------')
                    data['id'] = [getattr(ea, 'id') for ea in updates]
                    error_set.append(data)
            else:
                model = Model(**data)
                db.session.add(model)
                add_count += 1
                all_results.append(model)
    print('------------------------------------------------------------------------------')
    print(f'The all results has {len(all_results)} records to commit')
    print(f'This includes {update_count} updated records')
    print(f'This includes {add_count} added records')
    print(f'We were unable to handle {len(error_set)} of the incoming dataset items')
    print('------------------------------------------------------------------------------')
    db.session.commit()
    return [from_sql(ea) for ea in all_results]


def _create_database():
    """ May currently only work if we do not need to drop the tables before creating them """
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
