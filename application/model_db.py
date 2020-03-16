from flask import Flask, flash, current_app
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy import or_, desc
from flask_migrate import Migrate
from datetime import datetime as dt
from dateutil import parser
import re
from statistics import mean, median, stdev
import json
from pprint import pprint  # only for debugging

db = SQLAlchemy()
migrate = Migrate(current_app, db)


def init_app(app):
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)  # Disabled since it unnecessary uses memory
    # app.config.setdefault('SQLALCHEMY_ECHO', True)  # Turns on A LOT of logging.
    # app.config['MYSQL_DATABASE_CHARSET'] = 'utf8mb4'  # Perhaps already set by default in MySQL
    db.init_app(app)


def metric_clean(metric_string):
    return re.sub('^carousel_album_', '', metric_string)


def clean(obj):
    """ Make sure this obj is serializable. Datetime objects should be turned to strings. """
    if isinstance(obj, dt):
        return obj.isoformat()
    return obj


def from_sql(row, related=False, safe=True):
    """ Translates a SQLAlchemy model instance into a dictionary.
        Will return only viewable fields when 'safe' is True.
    """
    data = row.__dict__.copy()
    data['id'] = row.id
    if related:
        related_fields = []
        for name, rel in row.__mapper__.relationships.items():
            data[name] = getattr(row, name, [])
            related_fields.append(name)
        data['related'] = related_fields
    temp = data.pop('_sa_instance_state', None)
    if not temp:
        current_app.logger.error('Not a model instance!')
    if safe:
        Model = row.__class__
        data = {k: data[k] for k in data.keys() - Model.UNSAFE}
    return data


def fix_date(Model, data):
    datestring = ''
    if Model in {Insight, OnlineFollowers}:
        datestring = data.pop('end_time', None)
    elif Model == Audience:
        datestring = data.get('values', [{}])[0].get('end_time')  # We expect the list to have only 1 element.
    elif Model == Post:
        datestring = data.pop('timestamp', None)
    data['recorded'] = parser.isoparse(datestring).replace(tzinfo=None) if datestring else data.get('recorded')
    return data


class User(UserMixin, db.Model):
    """ Data model for user (influencer or brand) accounts.
        Assumes only 1 Instagram per user, and it must be a business account.
        They must have a Facebook Page connected to their business Instagram account.
    """
    roles = ('influencer', 'brand', 'manager', 'admin')
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.Enum(*roles, name='user_roles'), default='influencer', nullable=False)
    name = db.Column(db.String(47),                 index=False, unique=False, nullable=True)
    email = db.Column(db.String(191),               index=False, unique=True,  nullable=True)
    password = db.Column(db.String(191),            index=False, unique=False, nullable=True)
    instagram_id = db.Column(BIGINT(unsigned=True), index=True,  unique=True,  nullable=True)
    facebook_id = db.Column(BIGINT(unsigned=True),  index=False, unique=False, nullable=True)
    token = db.Column(db.String(255),               index=False, unique=False, nullable=True)
    token_expires = db.Column(db.DateTime,          index=False, unique=False, nullable=True)
    notes = db.Column(db.String(191),               index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime,               index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,                index=False, unique=False, nullable=False, default=dt.utcnow)
    insights = db.relationship('Insight',          backref='user', lazy=True, passive_deletes=True)
    audiences = db.relationship('Audience',        backref='user', lazy=True, passive_deletes=True)
    aud_count = db.relationship('OnlineFollowers', backref='user', lazy=True, passive_deletes=True)
    posts = db.relationship('Post',                backref='user', lazy=True, passive_deletes=True)  # ? query_class=GetActive,
    # # campaigns = backref from Campaign.users with lazy='dynamic'
    # # brand_campaigns = backref from Campaign.brands with lazy='dynamic'
    UNSAFE = {'password', 'token', 'token_expires', 'modified', 'created'}

    def __init__(self, *args, **kwargs):
        kwargs['facebook_id'] = kwargs.pop('id') if 'facebook_id' not in kwargs and 'id' in kwargs else None
        kwargs['name'] = kwargs.pop('username', kwargs.get('name'))
        if 'token_expires' not in kwargs and 'token' in kwargs:
            # modifications for parsing data from api call
            token_expires = kwargs['token'].get('token_expires', None)
            kwargs['token_expires'] = dt.fromtimestamp(token_expires) if token_expires else None
            kwargs['token'] = kwargs['token'].get('access_token', None)
        super().__init__(*args, **kwargs)

    def campaign_unprocessed(self, campaign):
        """ Returns a Query of this User's Posts that need to be determined if they belong to the given Campaign """
        posts = Post.query.filter(Post.user_id == self.id, ~Post.rejections.contains(campaign))
        return posts.order_by('recorded').all()

    def campaign_posts(self, campaign):
        """ Returns a Query of this User's Posts that are already assigned to the given Campaign """
        posts = Post.query.filter(Post.user_id == self.id, Post.campaigns.contains(campaign)).order_by('recorded').all()
        return [ea.display() for ea in posts]

    def campaign_rejected(self, campaign):
        """ Returns a Query of this User's Posts that have already been rejected for given Campaign """
        posts = Post.query.filter(Post.user_id == self.id, Post.rejections.contains(campaign))
        posts = posts.filter(~Post.campaigns.contains(campaign)).order_by('recorded').all()
        return [ea.display() for ea in posts]

    def recent_insight(self, metrics):
        """ What is the most recent date that we collected the given insight metrics """
        if metrics == 'influence' or metrics == Insight.influence_metrics:
            metrics = list(Insight.influence_metrics)
        elif metrics == 'profile' or metrics == Insight.profile_metrics:
            metrics = list(Insight.profile_metrics)
        elif isinstance(metrics, (list, tuple)):
            for ea in metrics:
                if ea not in Insight.metrics:
                    raise ValueError(f"{ea} is not a valid Insight metric")
        elif metrics in Insight.metrics:
            metrics = [metrics]
        else:
            raise ValueError(f"{metrics} is not a valid Insight metric")
        # TODO: ?Would it be more efficient to use self.insights?
        q = Insight.query.filter(Insight.user_id == self.id, Insight.name.in_(metrics))
        recent = q.order_by(desc('recorded')).first()
        date = getattr(recent, 'recorded', 0) if recent else 0
        current_app.logger.info(f"Recent Insight: {metrics} | {recent} ")
        current_app.logger.info('-------------------------------------')
        current_app.logger.info(date)
        return date

    def export_posts(self):
        """ Collect all posts for this user in a list of lists for populating a worksheet. """
        ignore = ['id', 'user_id']
        columns = [ea.name for ea in Post.__table__.columns if ea.name not in ignore]
        data = [[clean(getattr(post, ea, '')) for ea in columns] for post in self.posts]
        return [columns, *data]

    def insight_report(self):
        """ Collect all of the Insights (including OnlineFollowers) and prepare for data dump on a sheet """
        report = [
            [f"{self.role.capitalize()} Name", self.name],
            ["Notes", self.notes],
            ["Instagram ID", self.instagram_id],
            [''],
            ["Insights", len(self.insights), "records"],
            ["Name", "Value", "Date Recorded"]
        ]
        for insight in self.insights:
            report.append([insight.name, insight.value, clean(insight.recorded)])
        report.extend([
            [''],
            ["Online Followers", len(self.aud_count), "records"],
            ["Date", "Hour", "Value"]
        ])
        for data in self.aud_count:
            report.append([clean(data.recorded), int(data.hour), int(data.value)])
        report.extend([
            [''],
            ["Audience Information", len(self.audiences), "records"],
            ["Date Recorded", "Name", "Value"]
        ])
        for audience in self.audiences:
            report.append([clean(audience.recorded), audience.name, audience.value])
        report.append([''])
        return report

    def insight_summary(self, label_only=False):
        """ Used for giving summary stats of insight metrics for a Brand (or other user) """
        big_metrics = list(Insight.influence_metrics)
        big_stat = [('Median', median), ('Average', mean), ('StDev', stdev)]
        insight_labels = [f"{metric} {ea[0]}" for metric in big_metrics for ea in big_stat]
        small_metrics = list(Insight.profile_metrics)
        small_stat = [('Total', sum), ('Average', mean)]
        small_metric_labels = [f"{metric} {ea[0]}" for metric in small_metrics for ea in small_stat]
        insight_labels.extend(small_metric_labels)
        of_metrics = list(OnlineFollowers.metrics)
        of_stat = [('Median', median)]
        of_metric_lables = [f"{metric} {ea[0]}" for metric in of_metrics for ea in of_stat]
        insight_labels.extend(of_metric_lables)
        if label_only:
            return ['Brand Name', 'Notes', *insight_labels, 'instagram_id', 'modified', 'created']
        if self.instagram_id is None or not self.insights:
            insight_data = [0 for ea in insight_labels]
        else:
            met_stat = {metric: big_stat for metric in big_metrics}
            met_stat.update({metric: small_stat for metric in small_metrics})
            temp = {key: [] for key in met_stat}
            for insight in self.insights:
                temp[insight.name].append(int(insight.value))
            for metric in of_metrics:
                met_stat[metric] = of_stat
                temp[metric] = [int(ea.value) for ea in self.aud_count]
            insight_data = [stat[1](temp[metric]) for metric, stats in met_stat.items() for stat in stats]
        report = [self.name, self.notes, *insight_data, getattr(self, 'instagram_id', ''), clean(self.modified), clean(self.created)]
        return report

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<User - {}: {}>'.format(self.role, self.name)


class OnlineFollowers(db.Model):
    """ Data model for 'online_followers' for a user (influencer or brand) """
    composite_unique = ('user_id', 'recorded', 'hour')
    __tablename__ = 'onlinefollowers'
    __table_args__ = (db.UniqueConstraint(*composite_unique, name='uq_onlinefollowers_recorded_hour'),)

    id = db.Column(db.Integer,      primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime, index=False, unique=False, nullable=False)
    hour = db.Column(db.Integer,      index=False, unique=False, nullable=False)
    value = db.Column(db.Integer,     index=False, unique=False, nullable=True)
    # # user = backref from User.aud_count with lazy='select' (synonym for True)
    metrics = ['online_followers']
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        kwargs = fix_date(OnlineFollowers, kwargs)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return int(self.value)

    def __repr__(self):
        return f"<OnlineFollowers {self.recorded} | Hour: {self.hour} | User {self.user_id} >"


class Insight(db.Model):
    """ Data model for insights data on a (influencer or brand) user's account """
    composite_unique = ('user_id', 'recorded', 'name')
    __tablename__ = 'insights'
    __table_args__ = (db.UniqueConstraint(*composite_unique, name='uq_insights_recorded_name'),)

    id = db.Column(db.Integer,      primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime,          index=False, unique=False, nullable=False)
    name = db.Column(db.String(47),            index=False, unique=False, nullable=False)
    value = db.Column(db.Integer,              index=False, unique=False, nullable=True)
    # # user = backref from User.insights with lazy='select' (synonym for True)
    influence_metrics = {'impressions', 'reach'}
    profile_metrics = {'phone_call_clicks', 'text_message_clicks', 'email_contacts',
                       'get_directions_clicks', 'website_clicks', 'profile_views', 'follower_count'}
    metrics = influence_metrics.union(profile_metrics)
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
    composite_unique = ('user_id', 'recorded', 'name')
    __tablename__ = 'audiences'
    __table_args__ = (db.UniqueConstraint(*composite_unique, name='uq_audiences_recorded_name'),)

    id = db.Column(db.Integer,      primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime,          index=False, unique=False, nullable=False)
    name = db.Column(db.String(47),            index=False, unique=False, nullable=False)
    value = db.Column(db.Text,                 index=False, unique=False, nullable=True)
    # # user = backref from User.audiences with lazy='select' (synonym for True)
    metrics = {'audience_city', 'audience_country', 'audience_gender_age'}
    ig_data = {'media_count', 'followers_count'}  # these are created when assigning an instagram_id to a User
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        """ Clean out the not needed data from the API call. """
        kwargs = fix_date(Audience, kwargs)
        data, kwargs = kwargs.copy(), {}
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
    # # rejections = backref from Campaign.rejected with lazy='dynamic'
    # # campaigns = backref from Campaign.posts with lazy='dynamic'
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
        super().__init__(*args, **kwargs)

    def display(self):
        """ Since different media post types have different metrics, we only want to show the appropriate fields. """
        post = from_sql(self, related=False, safe=True)  # TODO: Allow related to show status in other campaigns
        fields = {'id', 'user_id', 'campaigns', 'rejections', 'recorded'}
        fields.update(Post.metrics['basic'])
        fields.discard('timestamp')
        fields.update(Post.metrics[post['media_type']])
        return {key: val for (key, val) in post.items() if key in fields}

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
    db.Column('brand_id',    db.Integer, db.ForeignKey('users.id',    ondelete="CASCADE")),
    db.Column('campaign_id', db.Integer, db.ForeignKey('campaigns.id', ondelete="CASCADE"))
)

post_campaign = db.Table(
    'post_campaigns',
    db.Column('id',          db.Integer, primary_key=True),
    db.Column('post_id',    db.Integer, db.ForeignKey('posts.id',    ondelete="CASCADE")),
    db.Column('campaign_id', db.Integer, db.ForeignKey('campaigns.id', ondelete="CASCADE"))
)

rejected_campaign = db.Table(
    'rejected_campaigns',
    db.Column('id',          db.Integer, primary_key=True),
    db.Column('post_id',    db.Integer, db.ForeignKey('posts.id',    ondelete="CASCADE")),
    db.Column('campaign_id', db.Integer, db.ForeignKey('campaigns.id', ondelete="CASCADE"))
)


class Campaign(db.Model):
    """ Model to manage the Campaign relationship between influencers and brands """
    __tablename__ = 'campaigns'

    id = db.Column(db.Integer,       primary_key=True)
    completed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(47),   index=True,  unique=True,  nullable=True)
    notes = db.Column(db.String(191), index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime, index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,  index=False, unique=False, nullable=False, default=dt.utcnow)
    users = db.relationship('User',    secondary=user_campaign, backref=db.backref('campaigns', lazy='dynamic'))
    brands = db.relationship('User',   secondary=brand_campaign, backref=db.backref('brand_campaigns', lazy='dynamic'))
    posts = db.relationship('Post',    secondary=post_campaign, backref=db.backref('campaigns', lazy='dynamic'))
    rejected = db.relationship('Post', secondary=rejected_campaign, backref=db.backref('rejections', lazy='dynamic'))
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        kwargs['completed'] = True if kwargs.get('completed') in {'on', True} else False
        super().__init__(*args, **kwargs)

    def export_posts(self):
        """ Used for Sheets Report, a top label row followed by rows of Posts data. """
        ignore = ['id', 'user_id']
        columns = [ea.name for ea in Post.__table__.columns if ea.name not in ignore]
        data = [[clean(getattr(post, ea, '')) for ea in columns] for post in self.posts]
        return [columns, *data]

    def get_results(self):
        """ We want the datasets and summary statistics """
        rejected = {'insight', 'basic'}
        added = {'comments_count', 'like_count'}
        lookup = {k: v.union(added) for k, v in Post.metrics.items() if k not in rejected}
        related, sets_list = {}, []
        for media_type, metric_set in lookup.items():
            temp = [metric_clean(ea) for ea in metric_set]
            sets_list.append(set(temp))
            related[media_type] = {'posts': [], 'metrics': {ea: [] for ea in temp}, 'labels': {ea: [] for ea in temp}}
        # add key for common metrics summary
        start = sets_list.pop()
        common = list(start.intersection(*sets_list))
        related['common'] = {'metrics': {metric: [] for metric in common}, 'labels': {metric: [] for metric in common}}
        # populate metric lists with data from this campaign's currently assigned posts.
        for post in self.posts:
            media_type = post.media_type
            related[media_type]['posts'].append(post)
            for metric in related[media_type]['metrics']:
                related[media_type]['metrics'][metric].append(int(getattr(post, metric)))
                related[media_type]['labels'][metric].append(int(getattr(post, 'id')))
                if metric in related['common']['metrics']:
                    related['common']['metrics'][metric].append(int(getattr(post, metric)))
                    related['common']['labels'][metric].append(int(getattr(post, 'id')))
        # compute stats we want for each media type and common metrics
        for group in related:
            # TODO: Modify the stats used as appropriate for the metric
            related[group]['results'] = {}
            metrics = related[group]['metrics']
            for metric, data in metrics.items():
                curr = {}
                curr['Total'] = sum(data) if len(data) > 0 else 0
                curr['Median'] = median(data) if len(data) > 0 else 0
                curr['Mean'] = mean(data) if len(data) > 0 else 0
                curr['StDev'] = stdev(data) if len(data) > 1 else 0
                related[group]['results'][metric] = curr
        return related

    def __str__(self):
        name = self.name if self.name else self.id
        brands = ', '.join([brand.name for brand in self.brands]) if self.brands else 'NA'
        return f"Campaign: {name} with Brand(s): {brands}"

    def __repr__(self):
        name = self.name if self.name else self.id
        brands = ', '.join([brand.name for brand in self.brands]) if self.brands else 'NA'
        return '<Campaign: {} | Brands: {} >'.format(name, brands)


def db_create(data, Model=User):
    try:
        model = Model(**data)
        db.session.add(model)
        db.session.commit()
    except IntegrityError as error:
        # most likely only happening on Brand, User, or Campaign
        current_app.logger.error('----------- IntegrityError Condition -------------------')
        current_app.logger.error(error)
        db.session.rollback()
        columns = Model.__table__.columns
        unique = {c.name: data.get(c.name) for c in columns if c.unique}
        pprint(unique)
        model = Model.query.filter(*[getattr(Model, key) == val for key, val in unique.items()]).one_or_none()
        if model:
            message = f"A {model.__class__.__name__} already exists with id: {model.id} . Using existing."
        else:
            message = f'Cannot create due to collision on unique fields. Cannot retrieve existing record'
        current_app.logger.error(message)
        flash(message)
    # except Exception as e:
    #     print('**************** DB CREATE Error *******************')
    #     print(e)
    return from_sql(model, related=False, safe=True)


def db_read(id, Model=User, related=False, safe=True):
    model = Model.query.get(id)
    return from_sql(model, related=related, safe=safe) if model else None


def db_update(data, id, related=False, Model=User):
    # Any checkbox field should have been prepared by process_form()
    # TODO: Look into using the method Model.update
    model = Model.query.get(id)
    associated = {name: data.pop(name) for name in model.__mapper__.relationships.keys() if data.get(name, None)}
    try:
        for k, v in data.items():
            setattr(model, k, v)
        for k, v in associated.items():
            if getattr(model, k, None):
                getattr(model, k).append(v)
            else:
                setattr(model, k, v)
        db.session.commit()
    except IntegrityError as e:
        current_app.logger.error(e)
        db.session.rollback()
        if Model == User:
            message = 'Found existing user. '
        else:
            message = "Input Error. Make sure values are unique where required, and confirm all inputs are valid."
        flash(message)
        raise ValueError(e)
    return from_sql(model, related=related, safe=True)


def db_delete(id, Model=User):
    Model.query.filter_by(id=id).delete()
    db.session.commit()


def db_all(Model=User, role=None):
    """ Returns all of the records for the indicated Model, or for User Model returns either brands or influencers. """
    query = Model.query
    if Model == User:
        role_type = role if role else 'influencer'
        query = query.filter_by(role=role_type)
    sort_field = Model.recorded if hasattr(Model, 'recorded') else Model.name if hasattr(Model, 'name') else Model.id
    # TODO: For each model declare default sort, then use that here: query.order_by(Model.<sortfield>).all()
    return query.order_by(sort_field).all()


def create_many(dataset, Model=User):
    """ Currently only used for temporary developer_admin function """
    all_results = []
    for data in dataset:
        model = Model(**data)
        db.session.add(model)
        all_results.append(model)
    db.session.commit()
    return [from_sql(ea, related=False, safe=False) for ea in all_results]


def db_create_or_update_many(dataset, user_id=None, Model=Post):
    """ Create or Update if the record exists for all of the dataset list """
    current_app.logger.info(f'============== Create or Update Many {Model.__name__} ====================')
    allowed_models = {Post, Insight, Audience, OnlineFollowers}
    if Model not in allowed_models:
        return []
    composite_unique = [ea for ea in getattr(Model, 'composite_unique', []) if ea != 'user_id']
    all_results, add_count, update_count, error_set = [], 0, 0, []
    if composite_unique and user_id:
        match = Model.query.filter(Model.user_id == user_id).all()
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
                # TODO: Look into Model.update method
                associated = {name: data.pop(name) for name in model.__mapper__.relationships.keys() if data.get(name)}
                for k, v in data.items():
                    setattr(model, k, v)
                for k, v in associated.items():
                    getattr(model, k).append(v)
                update_count += 1
            else:
                # print('No match in existing data')
                model = Model(**data)
                db.session.add(model)
                add_count += 1
            all_results.append(model)
    else:
        # The following should work with multiple single column unique fields, but no composite unique requirements
        # print('----------------- Unique Columns -----------------------')
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
            if len(updates):
                if len(updates) == 1:
                    model = updates[0]
                    associated = {name: data.pop(name) for name in model.__mapper__.relationships.keys() if data.get(name)}
                    for k, v in data.items():
                        setattr(model, k, v)
                    for k, v in associated.items():
                        getattr(model, k).append(v)
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
    current_app.logger.info('All records saved')
    return [from_sql(ea, related=False, safe=True) for ea in all_results]


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
