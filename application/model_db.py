from flask import Flask, flash, current_app
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy import or_, desc  # , and_, select, func
from sqlalchemy_utils import EncryptedType  # encrypt
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine  # encrypt
from cryptography.fernet import Fernet  # noqa: F401  # TODO: Is this needed here? # encrypt
from flask_migrate import Migrate
from datetime import datetime as dt
from dateutil import parser
import re
from statistics import mean, median, stdev
import json
# from .db_introspect_functions import check_stuff

db = SQLAlchemy()
migrate = Migrate(current_app, db)
SECRET_KEY = current_app.config.get('SECRET_KEY')


def init_app(app):
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)  # Disabled since it unnecessary uses memory
    # app.config.setdefault('SQLALCHEMY_ECHO', True)  # Turns on A LOT of logging.
    # app.config['MYSQL_DATABASE_CHARSET'] = 'utf8mb4'  # Perhaps already set by default in MySQL
    db.init_app(app)


def metric_clean(metric_string):
    """Removes the 'carousel_album_' from the beginning of the string to ensure a consistant structure of metrics. """
    return re.sub('^carousel_album_', '', metric_string)


def clean(obj):
    """Make sure this obj is serializable. Datetime objects should be turned to strings. """
    if isinstance(obj, dt):
        return obj.isoformat()
    elif isinstance(obj, (list, tuple)):
        # current_app.logger.info(f"================= Clean for obj: {obj} ====================")
        ' | '.join(obj)
    # elif isinstance(obj, (list, tuple, set)):
    #     temp = []
    #     for ea in obj:
    #         temp.append(clean(ea))
    #     return temp
    # elif isinstance(obj, (Campaign, User)):
    #     return obj.id
    return obj


def from_sql(row, related=False, safe=True):
    """Translates a SQLAlchemy model instance into a dictionary.
        Can return all properties, both column fields and properties declared by decorators.
        Will return ORM related fields unless 'related' is False.
        Will return only safe for viewing fields when 'safe' is True.
    """
    data = {k: getattr(row, k) for k in dir(row.__mapper__.all_orm_descriptors) if not k.startswith('_')}
    # check_stuff(row, related, safe)  # TODO: Remove after resolved.
    unwanted_keys = set()
    if not related:
        unwanted_keys.update(row.__mapper__.relationships)
    if safe:
        unwanted_keys.update(row.__class__.UNSAFE)
    if len(unwanted_keys):
        data = {k: data[k] for k in data.keys() - unwanted_keys}
    return data


def fix_date(Model, data):
    """Modify the dict with expected response from Graph API so the date is formatted as needed for the given Model. """
    datestring = ''
    if Model in {Insight, OnlineFollowers}:
        datestring = data.pop('end_time', None)
    elif Model == Audience:
        datestring = data.get('values', [{}])[0].get('end_time')  # We expect the list to have only 1 element.
    elif Model == Post:
        datestring = data.pop('timestamp', None)
    data['recorded'] = parser.isoparse(datestring).replace(tzinfo=None) if datestring else data.get('recorded')
    return data


def translate_api_user_token(data):
    """Returns the given dict with 'token' & 'token_expires' updated if 'token' is a Graph API formatted user token. """
    if 'token_expires' not in data and 'token' in data:  # modifications for parsing data from api call
        token_duration = data['token'].get('expires_in', None)
        token_time = data['token'].get('expires_at', None)
        token_expires = data['token'].get('token_expires', token_time)
        if token_duration and not token_expires:
            now_utc_stamp = dt.replace(tzinfo=dt.timezone.utc).timestamp()
            token_expires = (now_utc_stamp + token_duration).in_seconds()
        data['token_expires'] = dt.fromtimestamp(int(token_expires)) if token_expires else None
        # data['refresh_token'] = data['token'].get('refresh_token', None)
        data['token'] = data['token'].get('access_token', None)
    return data


class User(UserMixin, db.Model):
    """Data model for user (influencer or brand) accounts.
       Assumes only 1 Instagram per user, and it must be a business account.
       They must have a Facebook Page connected to their business Instagram account.
    """
    ROLES = ('influencer', 'brand', 'manager', 'admin')
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.Enum(*ROLES, name='user_roles'), default='influencer', nullable=False)
    name = db.Column(db.String(47),                 index=False, unique=False, nullable=True)
    email = db.Column(db.String(191),               index=False, unique=True,  nullable=True)
    password = db.Column(db.String(191),            index=False, unique=False, nullable=True)
    story_subscribed = db.Column(db.Boolean, default=False)
    page_token = db.Column(EncryptedType(db.String(255), SECRET_KEY, AesEngine, 'pkcs5'))  # encrypt
    page_id = db.Column(BIGINT(unsigned=True),      index=False, unique=True,  nullable=True)
    instagram_id = db.Column(BIGINT(unsigned=True), index=True,  unique=True,  nullable=True)
    facebook_id = db.Column(BIGINT(unsigned=True),  index=False, unique=False, nullable=True)
    token = db.Column(EncryptedType(db.String(255), SECRET_KEY, AesEngine, 'pkcs5'))  # encrypt
    # access_token = db.Column(EncryptedType(db.String(255), SECRET_KEY, AesEngine, 'pkcs5'))  # encrypt
    token_expires = db.Column(db.DateTime,          index=False, unique=False, nullable=True)
    notes = db.Column(db.String(191),               index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime,               unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,                unique=False, nullable=False, default=dt.utcnow)
    insights = db.relationship('Insight',          order_by='Insight.recorded', backref='user', passive_deletes=True)
    audiences = db.relationship('Audience',        order_by='Audience.recorded', backref='user', passive_deletes=True)
    aud_count = db.relationship('OnlineFollowers', order_by='OnlineFollowers.recorded', backref='user',
                                passive_deletes=True)
    posts = db.relationship('Post',                order_by='Post.recorded', backref='user', passive_deletes=True)
    # # campaigns = backref from Campaign.users has lazy='joined' on other side
    # # brand_campaigns = backref from Campaign.brands has lazy='joined' on other side
    UNSAFE = {'password', 'token', 'token_expires', 'page_token', 'modified', 'created'}

    def __init__(self, *args, **kwargs):
        temp_id = kwargs.pop('id', None)  # See if removing 'id' can be done earlier, where facebook_id' is set.
        kwargs['facebook_id'] = temp_id if 'facebook_id' not in kwargs else kwargs['facebook_id']
        kwargs['name'] = kwargs.pop('username', kwargs.get('name'))  # TODO: Confirm 'username' is no longer needed.
        kwargs = translate_api_user_token(kwargs)
        super().__init__(*args, **kwargs)

    @property
    def connected_campaigns(self):
        """Returns the campaigns or brand_campaigns for influencer or brand, respectively, or empty list otherwise. """
        if self.role == 'influencer':
            return self.campaigns
        elif self.role == 'brand':
            return self.brand_campaigns
        return []

    @property
    def full_token(self):
        """The dict structure of a full token generally received from the Graph API. The setter will extract values. """
        if not self.token:
            return None
        if self.token_expires:
            expires = (self.token_expires - dt.utcnow()).in_seconds()
            expires = 0 if expires < 0 else int(expires)
        else:
            expires = None
        result = {
            'access_token': self.token,
            # 'refresh_token': '',  # The FB Graph API does not use refresh_token.
            'token_type': 'Bearer',
            'expires_in': expires,
            }
        return result

    @full_token.setter
    def full_token(self, token):
        current_app.logger.info(f"Called full_token setter for {self} user. ")
        current_app.logger.info(token)
        # refresh_token = token.get('refresh_token', None)
        data = translate_api_user_token({'token': token})
        self.token_expires = data['token_expires']
        self.token = data['token']
        # current_app.logger.info(f"The {self} user has an unsaved refresh_token of {refresh_token} ")

    def get_auth_session(self):
        """Create an OAuth2Session for retrieving Graph API data for this user. """
        if not self.token:
            current_app.logger.error(f"Missing token for {self} user. Unable to create an OAuth2Session. ")
            return None
        # It seems that the Facebook Graph API does not have the auto_refresh_url and token_updater methods for OAuth2.
        facebook = OAuth2Session(current_app.config.get('FB_CLIENT_ID'), token=self.token)
        facebook = facebook_compliance_fix(facebook)
        return facebook

    # @hybrid_property
    # def is_connector(self):
    #     """Returns boolean: True if user has instagram_id and is an influencer or brand user. """
    #     return self.role in ('influencer', 'brand') and self.instagram_id is not None

    # @is_connector.expression
    # def is_connector(cls):
    #     return and_(cls.role.in_(['influencer', 'brand']), cls.instagram_id.is_not(None))

    # @is_connector.expression
    # def has_active_all(cls):
    #     is_active = Campaign.completed.is_(False)
    #     return and_(cls.role.in_('influencer', 'brand'), or_(cls.campaign(is_active), cls.brand_campaign(is_active)))

    @hybrid_property
    def has_active_all(self):
        """Returns boolean: True if associated to any currently active campaigns as either an Influencer or Brand. """
        has_influence = self.role == 'influencer' and any(ea.completed is False for ea in self.campaigns)
        has_brand = self.role == 'brand' and any(ea.completed is False for ea in self.brand_campaigns)
        return has_influence or has_brand

    # @has_active_all.expression
    # def has_active_all(cls):
    #     is_active = Campaign.completed.is_(False)
    #     # return cls.connected_campaigns.any(is_active)
    #     if cls.role == 'influencer':
    #         return cls.campaign.any(is_active)
    #     elif cls.role == 'brand':
    #         return cls.brand_campaign.any(is_active)
    #     users_z = User.query.filter(
    #         User.instagram_id.isnot(None),
    #         (or_(User.campaigns.any(is_active), User.brand_campaigns.any(is_active)))
    #         )
    #     return False

    # @hybrid_property
    # def active_all(self):
    #     """Returns boolean: True if associated to any currently active campaigns as either an Influencer or Brand. """
    #     has_influence = self.role == 'influencer' and any(ea.completed is False for ea in self.campaigns)
    #     has_brand = self.role == 'brand' and any(ea.completed is False for ea in self.brand_campaigns)
    #     return has_influence or has_brand

    # @active_all.expression
    # def active_all(cls):
    #     if cls.role not in ('influencer', 'brand'):
    #         return False
    #     is_active = Campaign.completed.is_(False)
    #     active = User.campaigns.any(is_active) if cls.role == 'influencer' else User.campaigns.any(is_active)
    #     # users_z = User.query.filter(User.instagram_id.isnot(None), (or_(User.campaigns.any(is_active), User.brand_campaigns.any(is_active))))
    #     return active

    # @hybrid_property
    # def has_active_special(self):
    #     """Returns boolean: True if associated to any currently active campaigns as either an Influencer or Brand. """
    #     has_influence = self.role == 'influencer' and any(ea.completed is False for ea in self.campaigns)
    #     has_brand = self.role == 'brand' and any(ea.completed is False for ea in self.brand_campaigns)
    #     return has_influence or has_brand

    # @hybrid_property
    # def has_active_connect(self):
    #     """Returns boolean: True if associated to any currently active campaigns as either an Influencer or Brand. """
    #     connected = self.connected_campaigns
    #     has_active_campaign = any(ea.completed is False for ea in connected)
    #     return has_active_campaign

    # @hybrid_property
    # def has_active_now(self):
    #     """Returns boolean: True if associated to any currently active campaigns as either an Influencer or Brand. """
    #     if self.role == 'influencer':
    #         active = any(ea.completed is False for ea in self.campaigns)
    #     elif self.role == 'brand':
    #         active = any(ea.completed is False for ea in self.brand_campaigns)
    #     else:
    #         active = False
    #     return active

    # @has_active_special.expression
    # def has_active_special(cls):
    #     has_infuence = cls.role == 'influencer' and select().join(user_campaign).join(Campaign)
    #     pass

    def has_active(self, ignore=[]):
        """Returns boolean: Similar to has_active_all, but if the ignore Campaigns(s) are not currently active. """
        # TODO: Turn into a hybrid_property for ignore=None, and a hybrid_method for ignore version?
        if not ignore:
            return self.has_active_all
        connected = self.connected_campaigns
        # if not isinstance(ignore, (list, tuple, set)):
        #     ignore = (ignore, ) if ignore else []
        if isinstance(ignore, (list, tuple)):
            ignore = set(ignore)
        elif not isinstance(ignore, set):
            ignore = set((ignore, ) if ignore else '')
        has_active_campaign = any(ea.completed is False for ea in connected if ea not in ignore)
        # connected_campaigns = [ea for ea in self.campaigns + self.brand_campaigns if ea not in ignore]
        # has_active_campaign = any(ea.completed is False for ea in connected_campaigns)
        return has_active_campaign

    def recent_insight(self, metrics):
        """What is the most recent date that we collected the given insight metrics """
        if metrics == 'influence' or metrics == Insight.INFLUENCE_METRICS:
            metrics = list(Insight.INFLUENCE_METRICS)
        elif metrics == 'profile' or metrics == Insight.PROFILE_METRICS:
            metrics = list(Insight.PROFILE_METRICS)
        elif isinstance(metrics, (list, tuple)):
            for ea in metrics:
                if ea not in Insight.METRICS:
                    raise ValueError(f"{ea} is not a valid Insight metric")
        elif metrics in Insight.METRICS:
            metrics = [metrics]
        else:
            raise ValueError(f"{metrics} is not a valid Insight metric")
        # TODO: ?Would it be more efficient to use self.insights?
        q = Insight.query.filter(Insight.user_id == self.id, Insight.name.in_(metrics))
        recent = q.order_by(desc('recorded')).first()
        date = getattr(recent, 'recorded', 0) if recent else 0
        current_app.logger.debug(f"Recent Insight: {metrics} | {recent} ")
        current_app.logger.debug('-------------------------------------')
        current_app.logger.debug(date)
        return date

    def export_posts(self):
        """Collect all posts for this user in a list of lists for populating a worksheet. """
        # TODO: Use code similar to Campaign.export_posts() ?
        ignore = ['id', 'user_id']
        columns = [ea.name for ea in Post.__table__.columns if ea.name not in ignore]
        data = [[clean(getattr(post, ea, '')) for ea in columns] for post in self.posts]
        return [columns, *data]

    def insight_report(self):
        """Collect all of the Insights (including OnlineFollowers) and prepare for data dump on a sheet """
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
        """Used for Sheet report: giving summary stats of insight metrics for a Brand (or other user). """
        big_metrics = list(Insight.INFLUENCE_METRICS)
        big_stat = [('Median', median), ('Average', mean), ('StDev', stdev)]
        insight_labels = [f"{metric} {ea[0]}" for metric in big_metrics for ea in big_stat]
        small_metrics = list(Insight.PROFILE_METRICS)
        small_stat = [('Total', sum), ('Average', mean)]
        small_metric_labels = [f"{metric} {ea[0]}" for metric in small_metrics for ea in small_stat]
        insight_labels.extend(small_metric_labels)
        of_metrics = list(OnlineFollowers.METRICS)
        of_stat = [('Median', median)]
        of_metric_lables = [f"{metric} {ea[0]}" for metric in of_metrics for ea in of_stat]
        insight_labels.extend(of_metric_lables)
        if label_only:
            return ['Brand Name', 'Notes', *insight_labels, 'instagram_id', 'modified', 'created']
        ig_id = getattr(self, 'instagram_id', '')
        if self.instagram_id is None or not self.insights:
            insight_data = [0 for ea in insight_labels]
        else:
            met_stat = {metric: big_stat for metric in big_metrics}
            met_stat.update({metric: small_stat for metric in small_metrics})
            temp = {key: [] for key in met_stat}
            for insight in self.insights:
                temp[insight.name].append(int(insight.value or 0))
            for metric in of_metrics:
                met_stat[metric] = of_stat
                temp[metric] = [int(ea.value or 0) for ea in self.aud_count]
            insight_data = [stat[1](temp[metric]) for metric, stats in met_stat.items() for stat in stats]
        report = [self.name, self.notes, *insight_data, ig_id, clean(self.modified), clean(self.created)]
        return report

    def __str__(self):
        # return f"{self.role} - {self.name}"
        return self.name or f"{self.role}: {self.id}"

    def __repr__(self):
        return '<User - {}: {}>'.format(self.role, self.name)


class DeletedUser:
    """Used as a placeholder for a user who has been deleted, but we still have data on their posts. """

    def __init__(self):
        self.id = 'na'
        self.role = 'deleted'
        self.name = 'Deleted User'
        super().__init__()

    def __str__(self):
        # return f"{self.role} - {self.name}"
        return self.name

    def __repr__(self):
        return '<User - {}: {}>'.format(self.role, self.name)


class OnlineFollowers(db.Model):
    """Data model for 'online_followers' for a user (influencer or brand) """
    COMPOSITE_UNIQUE = ('user_id', 'recorded', 'hour')
    __tablename__ = 'onlinefollowers'
    __table_args__ = (db.UniqueConstraint(*COMPOSITE_UNIQUE, name='uq_onlinefollowers_recorded_hour'),)

    id = db.Column(db.Integer,      primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime, index=False, unique=False, nullable=False)
    hour = db.Column(db.Integer,      index=False, unique=False, nullable=False)
    value = db.Column(db.Integer,     index=False, unique=False, nullable=False, default=0)
    # # user = backref from User.aud_count
    METRICS = ['online_followers']
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        kwargs = fix_date(OnlineFollowers, kwargs)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.recorded} - {self.hour}: {str(int(self.value or 0))} "

    def __repr__(self):
        return f"<OnlineFollowers {self.recorded} | Hour: {self.hour} | User {self.user_id} >"


class Insight(db.Model):
    """Data model for insights data on a (influencer or brand) user's account """
    COMPOSITE_UNIQUE = ('user_id', 'recorded', 'name')
    __tablename__ = 'insights'
    __table_args__ = (db.UniqueConstraint(*COMPOSITE_UNIQUE, name='uq_insights_recorded_name'),)

    id = db.Column(db.Integer,      primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime,          index=False, unique=False, nullable=False)
    name = db.Column(db.String(47),            index=False, unique=False, nullable=False)
    value = db.Column(db.Integer,              index=False, unique=False, nullable=False, default=0)
    # # user = backref from User.insights
    INFLUENCE_METRICS = {'impressions', 'reach'}
    PROFILE_METRICS = {'phone_call_clicks', 'text_message_clicks', 'email_contacts',
                       'get_directions_clicks', 'website_clicks', 'profile_views', 'follower_count'}
    METRICS = INFLUENCE_METRICS.union(PROFILE_METRICS)
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        kwargs = fix_date(Insight, kwargs)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"Insight - {self.name} on {self.recorded} User: {self.user_id}"

    def __repr__(self):
        return '<Insight: {} | User: {} | Date: {} >'.format(self.name, self.user_id, self.recorded)


class Audience(db.Model):
    """Data model for current information about the user's audience. """
    # TODO: If this data not taken over by Neo4j, then refactor to parse out the age groups and gender groups
    COMPOSITE_UNIQUE = ('user_id', 'recorded', 'name')
    __tablename__ = 'audiences'
    __table_args__ = (db.UniqueConstraint(*COMPOSITE_UNIQUE, name='uq_audiences_recorded_name'),)

    id = db.Column(db.Integer,      primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    recorded = db.Column(db.DateTime,          index=False, unique=False, nullable=False)
    name = db.Column(db.String(47),            index=False, unique=False, nullable=False)
    value = db.Column(db.Text,                 index=False, unique=False, nullable=True)
    # # user = backref from User.audiences
    METRICS = {'audience_city', 'audience_country', 'audience_gender_age'}
    IG_DATA = {'media_count', 'followers_count'}  # these are created when assigning an instagram_id to a User
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        """Initializes the instance after cleaning out the not needed data from the API call. """
        kwargs = fix_date(Audience, kwargs)
        data, kwargs = kwargs.copy(), {}
        kwargs['recorded'] = data.get('recorded')
        kwargs['user_id'] = data.get('user_id')
        kwargs['name'] = re.sub('^audience_', '', data.get('name'))
        kwargs['value'] = data.get('value', json.dumps(data.get('values', [{}])[0].get('value')))
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"Audience - {self.name} on {self.recorded} User: {self.user_id}"

    def __repr__(self):
        return '<Audience {} | User: {} | Date: {} >'.format(self.name, self.user_id, self.recorded)


class Post(db.Model):
    """Instagram media that was posted by an influencer or brand user """
    __tablename__ = 'posts'

    id = db.Column(db.Integer,          primary_key=True)
    user_id = db.Column(db.Integer,     db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    media_id = db.Column(BIGINT(unsigned=True), index=True,  unique=True,  nullable=False)
    media_type = db.Column(db.String(47),       index=False, unique=False, nullable=True)
    caption = db.Column(db.Text,                index=False, unique=False, nullable=True)
    comments_count = db.Column(db.Integer,      index=False, unique=False, nullable=False, default=0)
    like_count = db.Column(db.Integer,          index=False, unique=False, nullable=False, default=0)
    permalink = db.Column(db.String(191),       index=False, unique=False, nullable=True)
    _saved_media = db.Column('saved_media', db.Text, index=False, unique=False, nullable=True)
    capture_name = db.Column(db.String(191),    index=False, unique=False, nullable=True)
    recorded = db.Column(db.DateTime,           index=False, unique=False, nullable=False)  # timestamp*
    modified = db.Column(db.DateTime,           unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,            unique=False, nullable=False, default=dt.utcnow)
    # The following 9 are from insights, the first 2 for all kinds of media
    impressions = db.Column(db.Integer,         index=False,  unique=False, nullable=False, default=0)
    reach = db.Column(db.Integer,               index=False,  unique=False, nullable=False, default=0)
    # The following 3 are for Album and Photo/Video media
    engagement = db.Column(db.Integer,          index=False,  unique=False, nullable=False, default=0)
    saved = db.Column(db.Integer,               index=False,  unique=False, nullable=False, default=0)
    video_views = db.Column(db.Integer,         index=False,  unique=False, nullable=False, default=0)
    # The following 4 are only for stories media
    exits = db.Column(db.Integer,               index=False,  unique=False, nullable=False, default=0)
    replies = db.Column(db.Integer,             index=False,  unique=False, nullable=False, default=0)
    taps_forward = db.Column(db.Integer,        index=False,  unique=False, nullable=False, default=0)
    taps_back = db.Column(db.Integer,           index=False,  unique=False, nullable=False, default=0)
    # # user = backref from User.posts
    # # processed = backref from Campaign.processed
    # # campaigns = backref from Campaign.posts
    METRICS = {}
    METRICS['basic'] = {'media_type', 'caption', 'comments_count', 'like_count', 'permalink', 'timestamp'}
    METRICS['insight'] = {'impressions', 'reach'}
    METRICS['IMAGE'] = {'engagement', 'saved'}.union(METRICS['insight'])
    METRICS['VIDEO'] = {'video_views'}.union(METRICS['IMAGE'])
    METRICS['CAROUSEL_ALBUM'] = {f"carousel_album_{metric}" for metric in METRICS['IMAGE']}  # ?in METRICS['VIDEO']
    METRICS['STORY'] = {'exits', 'replies', 'taps_forward', 'taps_back'}.union(METRICS['insight'])
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        kwargs = fix_date(Post, kwargs)
        super().__init__(*args, **kwargs)

    @hybrid_property
    def saved_media(self):
        """Returns the first listed url in _saved_media (after translating from json), or returns None if no value. """
        return None if self._saved_media is None else json.loads(self._saved_media)[0]

    @saved_media.setter
    def saved_media(self, saved_urls, display=0):
        """Saves a list of url strings, with the one in the 'display' position as the canonical url. """
        if not isinstance(saved_urls, (list, tuple, type(None))):
            raise TypeError("The saved_media must be a list of strings for the urls, or None. ")
        if not isinstance(display, int):
            raise TypeError("The display keyword must be set to an integer. ")
        elif saved_urls and display > len(saved_urls) - 1:
            raise ValueError("The display keyword was out of bounds for the input list. ")
        elif display != 0 and saved_urls:
            saved_urls[display], saved_urls[0] = saved_urls[0], saved_urls[display]
        self._saved_media = json.dumps(saved_urls) if saved_urls else None

    @hybrid_property
    def saved_media_options(self):
        """Return the list of all saved_media url links. """
        return None if self._saved_media is None else json.loads(self._saved_media)

    @saved_media_options.setter
    def saved_media_options(self, saved_urls):
        """Saves a list of url strings, making the first the canonical url. """
        self.saved_media(saved_urls, display=0)

    def display(self):
        """Since different media post types have different metrics, we only want to show the appropriate fields. """
        post = from_sql(self, related=True, safe=True)
        fields = {'id', 'user_id', 'saved_media', 'saved_media_options', 'capture_name', 'campaigns', 'processed'}
        fields.update(('recorded', 'modified'), Post.METRICS['basic'], Post.METRICS[post['media_type']])
        fields.discard('timestamp')
        # return {key: post[key] for key in post.keys() - fields}
        return {key: val for (key, val) in post.items() if key in fields}

    def __str__(self):
        return f"{self.media_type} Post on {self.recorded} User: {self.user_id}"

    def __repr__(self):
        return '< {} Post | User: {} | Recorded: {} >'.format(self.media_type, self.user_id, self.recorded)


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

processed_campaign = db.Table(
    'processed_campaigns',
    db.Column('id',          db.Integer, primary_key=True),
    db.Column('post_id',     db.Integer, db.ForeignKey('posts.id',    ondelete="CASCADE")),
    db.Column('campaign_id', db.Integer, db.ForeignKey('campaigns.id', ondelete="CASCADE"))
    )


class Campaign(db.Model):
    """Model to manage the Campaign relationship between influencers and brands """
    __tablename__ = 'campaigns'

    id = db.Column(db.Integer,       primary_key=True)
    completed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(47),   index=True,  unique=True,  nullable=True)
    notes = db.Column(db.String(191), index=False, unique=False, nullable=True)
    modified = db.Column(db.DateTime, index=False, unique=False, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)
    created = db.Column(db.DateTime,  index=False, unique=False, nullable=False, default=dt.utcnow)
    users = db.relationship('User',   lazy='joined',             secondary=user_campaign, backref='campaigns')
    brands = db.relationship('User',  lazy='joined',             secondary=brand_campaign, backref='brand_campaigns')
    posts = db.relationship('Post',     order_by='Post.recorded', secondary=post_campaign, backref='campaigns')
    processed = db.relationship('Post', order_by='Post.recorded', secondary=processed_campaign, backref='processed')
    # TODO: Method so posts, and rejected (subset of processed) can be grouped by user and then sorted by recorded.
    # Currently this functionality is solved with method calls to each influencer User account connected to a campaign.
    UNSAFE = {''}

    def __init__(self, *args, **kwargs):
        kwargs['completed'] = True if kwargs.get('completed') in {'on', True} else False
        super().__init__(*args, **kwargs)

    def export_posts(self):
        """Used for Sheets Report, a top label row followed by rows of Posts data. """
        ignore = {'id', 'user_id'}
        ignore.update(Post.UNSAFE)
        ignore.update(Post.__mapper__.relationships.keys())  # TODO: Decide if we actually want to keep related models?
        properties = [k for k in dir(Post.__mapper__.all_orm_descriptors) if not k.startswith('_') and k not in ignore]
        data = [[clean(getattr(post, ea, '')) for ea in properties] for post in self.posts]
        return [properties, *data]

    def related_posts(self, view):
        """Used for the different campaign management views. """
        allowed_view_values = ('management', 'collected', 'rejected')
        if view not in allowed_view_values:
            raise ValueError(f"The passed parameter was {view} and did not match {allowed_view_values}. ")
        related = {user: [] for user in self.users}
        deleted_user = DeletedUser()
        related[deleted_user] = []
        if view == 'management':
            for user in self.users:
                related[user] = [post for post in user.posts if post not in self.processed]
                # TODO: Need a faster process. Would refactor to return a query be better?
        elif view == 'rejected':
            for post in self.processed:
                # if post not in self.posts:
                if self not in post.campaigns:
                    user = deleted_user if post.user_id is None else post.user
                    related[user].append(post.display())
        elif view == 'collected':
            for post in self.posts:
                user = deleted_user if post.user_id is None else post.user
                related[user].append(post.display())
        if not len(related[deleted_user]):
            del related[deleted_user]
        return related

    def get_results(self):
        """We want the datasets and summary statistics. Used for results view as preview before creating sheet. """
        # when finished, related is a dictionary with the following format:
        # {media_type: {
        #               'posts': [],
        #               'metrics': {metric: []},
        #               'labels':  {metric: []},
        #               'results': {metric: {
        #                                    'Total': 0,
        #                                    'Median': 0,
        #                                    'Mean': 0,
        #                                    'StDev': 0
        #                                    }
        #                           }
        #               }
        #  'common':   {
        #               'metrics' {metric: []},
        #               'labels': {metric: []}
        #               'results': {metric: {
        #                                    'Total': 0,
        #                                    'Median': 0,
        #                                    'Mean': 0,
        #                                    'StDev': 0
        #                                    }
        #                           }
        #               }
        # }
        rejected = {'insight', 'basic'}
        added = {'comments_count', 'like_count'}
        lookup = {k: v.union(added) for k, v in Post.METRICS.items() if k not in rejected}
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
                related[media_type]['metrics'][metric].append(int(getattr(post, metric) or 0))
                related[media_type]['labels'][metric].append(int(getattr(post, 'id')))
                if metric in related['common']['metrics']:
                    related['common']['metrics'][metric].append(int(getattr(post, metric) or 0))
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
        name = self.name if self.name else str(self.id)
        brand_count = len(self.brands)
        if brand_count > 2:
            brands = f"{brand_count} Brands"
        else:
            brands = ', '.join(brand.name for brand in self.brands) if self.brands else 'NA'
        influencer_count = len(self.users)
        if influencer_count > 2:
            influencers = f"{influencer_count} Influencers"
        else:
            influencers = ', '.join(user.name for user in self.users) if self.users else 'NA'
        return f"{name} with {brands} and {influencers}"

    def __repr__(self):
        name = self.name if self.name else self.id
        return '<Campaign: {} | {} Brands | {} Influencers >'.format(name, len(self.brands), len(self.users))


def db_create(data, Model=User):
    """Creates a new model instance and returns a dictionary of its values. Used in add_edit, signup, & onboarding. """
    model = None
    try:
        model = Model(**data)
        db.session.add(model)
        db.session.commit()
    except IntegrityError as error:  # most likely only happening on Brand, User, or Campaign
        current_app.logger.error('----------- IntegrityError Condition -------------------')
        current_app.logger.error(error)
        db.session.rollback()
        columns = Model.__table__.columns
        unique = {c.name: data.get(c.name) for c in columns if c.unique}  # ?? pprint(unique)
        current_app.logger.debug(unique)
        model = Model.query.filter(*[getattr(Model, key) == val for key, val in unique.items()]).one_or_none()
        if model and Model == User:
            message = f"Using existing account. Welcome back {model.get('name', '')}! "
        elif model:
            message = f"A {model.__class__.__name__} already exists with id: {model.id} . Using existing. "
        else:
            message = "Cannot create due to collision on unique fields. Cannot retrieve existing record. "
        current_app.logger.error(message)
        flash(message)
    except Exception as e:
        current_app.logger.error('**************** DB CREATE Error *******************')
        current_app.logger.exception(e)
    return from_sql(model, related=False, safe=True)


def db_read(id, Model=User, related=False, safe=True):
    """Returns a dictionary of a model instance, defaulting to safe to view output, with optional related fields. """
    model = Model.query.get(id)
    return from_sql(model, related=related, safe=safe) if model else None


def db_update(data, id, related=False, Model=User):
    """Updates a model, replacing related if in the update data, and returns a safe to view dict of the model.  """
    # Any boolean field (as a checkbox in an HTML form) should have been prepared by process_form()
    # TODO: Look into using the method Model.update
    model = Model.query.get(id)
    associated = {name: data.pop(name) for name in model.__mapper__.relationships.keys() if data.get(name, None)}
    try:
        for k, v in data.items():
            setattr(model, k, v)
        for k, v in associated.items():
            # if getattr(model, k, None):
            #     temp = v if isinstance(v, (list, tuple)) else [v]
            #     for t in temp:
            #         getattr(model, k).append(t)
            # else:
            setattr(model, k, v)
        db.session.commit()
    except IntegrityError as e:
        current_app.logger.exception(e)
        db.session.rollback()
        if Model == User:
            message = "Found existing user. "
        else:
            message = "Input Error. Make sure values are unique where required, and confirm all inputs are valid. "
        flash(message)
        raise ValueError(e)
    except Exception as e:  # TODO: Remove this except catch and log after confirming no consistant issues.
        current_app.logger.info("===== Got a non-IntegrityError in db_update =====")
        current_app.logger.info(model)
        current_app.logger.info(associated)
        current_app.logger.info("-------------------------------------------------")
        current_app.logger.error(e)
        current_app.logger.info("-------------------------------------------------")
        raise e
    return from_sql(model, related=related, safe=True)


def db_delete(id, Model=User):
    """Deletes the given Model with the given 'id' from the database. """
    Model.query.filter_by(id=id).delete()
    db.session.commit()


def db_all(Model=User, role=None):
    """Returns all of the records for the indicated Model, or for User Model returns either brands or influencers. """
    query = Model.query
    if Model == User:
        role_type = role if role else 'influencer'
        query = query.filter_by(role=role_type)
    if Model == Campaign and role != 'all':
        only_completed = True if role == 'completed' else False
        query = query.filter_by(completed=only_completed)
    sort_field = Model.recorded if hasattr(Model, 'recorded') else Model.name if hasattr(Model, 'name') else Model.id
    # TODO: For each model declare default sort, then use that here: query.order_by(Model.<sortfield>).all()
    return query.order_by(sort_field).all()


def create_many(dataset, Model=User):
    """Currently only used for temporary developer_admin function """
    all_results = []
    for data in dataset:
        model = Model(**data)
        db.session.add(model)
        all_results.append(model)
    db.session.commit()
    return [from_sql(ea, related=False, safe=False) for ea in all_results]


def db_create_or_update_many(dataset, user_id=None, Model=Post):
    """Create or Update if the record exists for all of the dataset list. Returns a list of Model objects. """
    current_app.logger.info(f'============== Create or Update Many {Model.__name__} ====================')
    allowed_models = {Post, Insight, Audience, OnlineFollowers}
    if Model not in allowed_models:
        return []
    composite_unique = [ea for ea in getattr(Model, 'COMPOSITE_UNIQUE', []) if ea != 'user_id']
    all_results, add_count, update_count, error_set = [], 0, 0, []
    if composite_unique and user_id:
        match = Model.query.filter(Model.user_id == user_id).all()
        current_app.logger.debug(f'------ Composite Unique for {Model.__name__}: {len(match)} possible matches ------')
        lookup = {tuple([getattr(ea, key) for key in composite_unique]): ea for ea in match}
        for data in dataset:
            data = fix_date(Model, data)  # fix incoming data 'recorded' as needed for this Model
            # TODO: The following patch for Audience is not needed once we improve API validation process
            if Model == Audience:
                data['name'] = re.sub('^audience_', '', data.get('name'))
                data['value'] = json.dumps(data.get('values', [{}])[0].get('value'))
                data.pop('id', None)
            key = tuple([data.get(ea) for ea in composite_unique])
            model = lookup.get(key, None)
            current_app.logger.debug(f'------- {key} -------')
            if model:  # TODO: Look into Model.update method
                associated = {name: data.pop(name) for name in model.__mapper__.relationships.keys() if data.get(name)}
                for k, v in data.items():
                    setattr(model, k, v)
                for k, v in associated.items():
                    getattr(model, k).append(v)
                update_count += 1
            else:
                current_app.logger.debug('No match in existing data')
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
        # unique now has a key & list of values from the dataset for unique model fields.
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
            updates = [lookup[int(data[u_key])] for u_key, lookup in match_dict.items() if int(data[u_key]) in lookup]
            if len(updates):
                if len(updates) == 1:
                    model = updates[0]
                    associated = {name: data.pop(name) for name in model.__mapper__.relationships if data.get(name)}
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
    current_app.logger.info('------------------------------------------------------------------------------')
    current_app.logger.info(f'The all results has {len(all_results)} records to commit')
    current_app.logger.info(f'This includes {update_count} updated records')
    current_app.logger.info(f'This includes {add_count} added records')
    current_app.logger.info(f'We were unable to handle {len(error_set)} of the incoming dataset items')
    current_app.logger.info('------------------------------------------------------------------------------')
    db.session.commit()
    current_app.logger.info('All records saved')
    # return [from_sql(ea, related=False, safe=True) for ea in all_results]
    return all_results


def _create_database():
    """May currently only work if we do not need to drop the tables before creating them """
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
