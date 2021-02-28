from flask import current_app as app
from functools import wraps
from flask_login import current_user
from sqlalchemy import or_
from .model_db import User, Insight, Audience, Post, Campaign, db  # , user_campaign, brand_campaign,
from datetime import timedelta, datetime as dt
from time import time
import json


def mod_lookup(mod):
    """Associate to the appropriate Model, or raise error if 'mod' is not an expected value """
    if not isinstance(mod, str):
        raise TypeError("Expected a string input. ")
    lookup = {'insight': Insight, 'audience': Audience, 'post': Post, 'campaign': Campaign}
    lookup.update({role: User for role in User.ROLES})
    Model = lookup.get(mod, None)
    if not Model:
        raise ValueError("That is not a valid url path. ")
    return Model


def prep_ig_decide(data):
    """Some needed changes to prepare for the user to select amongst various Instagram accounts and data. """
    app.logger.info("Decide which IG account")
    ig_list = []
    for ig_info in data:
        cleaned = {}
        for key, value in ig_info.items():
            cleaned[key] = json.dumps(value) if key in Audience.IG_DATA else value
        ig_list.append(cleaned)
    app.logger.debug(f"Amongst these IG options: {ig_list}. ")
    return ig_list


def staff_required(role=['admin', 'manager']):
    """This decorator will allow use to limit access to routes based on user role. """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in role:
                app.logger.debug("Unauthorized for STAFF attempt. ")
                return app.login_manager.unauthorized()
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


def admin_required(role=['admin']):  # staff_required(role=role)
    """This decorator will limit access to admin only """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in role:
                app.logger.debug("Unauthorized for ADMIN attempt. ")
                return app.login_manager.unauthorized()
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


def self_or_staff_required(role=['admin', 'manager'], user=current_user):
    """This decorator limits access to staff or if the resource belongs to the current_user. """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in role:
                # TODO: Logic for testing if current_user is self for this model.
                app.logger.debug("Unauthorized for SELF OR STAFF attempt. ")
                return app.login_manager.unauthorized()
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


def get_daily_ig_accounts(active=True):
    """Returns a Query of Users that should have up-to-date tracking of their daily IG media posts. """
    # users = User.query.filter(User.instagram_id.isnot(None))
    # if active:
    #     is_active = Campaign.completed.is_(False)
    #     users = users.filter(or_(User.campaigns.any(is_active), User.brand_campaigns.any(is_active)))
    # return users
    influencers = User.query.join(Campaign.users)
    brands = User.query.join(Campaign.brands)
    users = influencers.union(brands)
    users = users.filter(User.instagram_id.isnot(None))
    if active:
        users = users.filter(Campaign.completed.is_(False))
    return users


def get_test_ig(version):
    """Trying a few structures to test their speed. """
    # results = {'version': ('query', 'query_result', 'duration')}
    results = (None, None, 0, 0)
    if version == 'a':
        start = time()
        users = User.query.filter(User.has_active_all.is_(True))
        result = users.all()
        end = time()
        results = (users, result, len(result), end - start, )
    # elif version == 'b':
    #     start = time()
    #     users = User.query.filter(User.has_active_special is True)
    #     result = users.all()
    #     end = time()
    #     results = (users, result, len(result), end - start, )
    # elif version == 'c':
    #     start = time()
    #     users = User.query.filter(User.has_active_special.is_(True))
    #     result = users.all()
    #     end = time()
    #     results = (users, result, len(result), end - start, )
    # elif version == 'd':
    #     start = time()
    #     users = User.query.filter(User.has_active_connect.is_(True))
    #     result = users.all()
    #     end = time()
    #     results = (users, result, len(result), end - start, )
    # elif version == 'e':
    #     start = time()
    #     users = User.query.filter(User.has_active_now.is_(True))
    #     result = users.all()
    #     end = time()
    #     results = (users, result, len(result), end - start, )

    # start_a = time()
    # active_i = User.query.join(user_campaign).join(Campaign).filter(Campaign.completed is False)
    # active_b = User.query.join(brand_campaign).join(Campaign).filter(Campaign.completed is False)
    # active_lla = active_i.union(active_b)
    # result_a = active_lla.all()
    # end_a = time()
    # results['a'] = (active_lla, result_a, end_a - start_a, )
    # db.session.flush()

    # start_b = time()
    # activei = User.query.join(user_campaign).join(Campaign)
    # activeb = User.query.join(brand_campaign).join(Campaign)
    # active_llb = activei.union(activeb).filter(Campaign.completed is False)
    # result_b = active_llb.all()
    # end_b = time()
    # results['b'] = (active_llb, result_b, end_b - start_b, )
    # db.session.flush()

    # start_c = time()
    # i_active = Campaign.query.join(user_campaign).join(User).filter(Campaign.completed is False)
    # b_active = Campaign.query.join(brand_campaign).join(User).filter(Campaign.completed is False)
    # active_llc = i_active.union(b_active)
    # result_c = active_llc.all()
    # end_c = time()
    # results['c'] = (active_llc, result_c, end_c - start_c, )
    # db.session.flush()

    # start_d = time()
    # iactive = Campaign.query.join(user_campaign).join(User)
    # bactive = Campaign.query.join(brand_campaign).join(User)
    # active_ll_d = iactive.union(bactive).filter(Campaign.completed is False)
    # result_d = active_ll_d.all()
    # end_d = time()
    # results['d'] = (active_ll_d, result_d, end_d - start_d, )
    # db.session.flush()

    # start_e = time()
    # initial_e = Campaign.query.filter(Campaign.completed is False)
    # iactive = initial_e.join(user_campaign).join(User)
    # bactive = initial_e.join(brand_campaign).join(User)
    # active_ll_e = iactive.union(bactive)
    # result_e = active_ll_e.all()
    # end_e = time()
    # results['e'] = (active_ll_e, result_e, end_e - start_e, )
    # db.session.flush()
    elif version == 'x':
        start_x = time()
        got_active = Campaign.completed.is_(False)
        users_x = User.query.filter(or_(User.campaigns.any(got_active), User.brand_campaigns.any(got_active)))
        result_x = users_x.all()
        end_x = time()
        result = (users_x, result_x, len(result_x), end_x - start_x, )
    elif version == 'y':
        start_y = time()
        has_active = Campaign.completed.is_(False)
        users_y = User.query.filter(User.instagram_id.isnot(None))
        users_y = users_y.filter(or_(User.campaigns.any(has_active), User.brand_campaigns.any(has_active)))
        result_y = users_y.all()
        end_y = time()
        results = (users_y, result_y, len(result_y), end_y - start_y, )
    elif version == 'z':
        start_z = time()
        is_active = Campaign.completed.is_(False)
        users_z = User.query.filter(User.instagram_id.isnot(None), (or_(User.campaigns.any(is_active), User.brand_campaigns.any(is_active))))
        result_z = users_z.all()
        end_z = time()
        results = (users_z, result_z, len(result_z), end_z - start_z, )

    db.session.flush()
    return results


def timeit(func, *args, **kwargs):
    """Determines the process time of the given callable when it is passed the given args and kwargs. """
    start = time()
    result = func(*args, **kwargs)
    end = time()
    dur = end - start
    return result, dur


def make_missing_timestamp(days_ago=0):
    """Returns a timestamp that is the given number of days in the past from now in UTC. """
    result = dt.utcnow()
    if days_ago:
        result -= timedelta(days=days_ago)
    return result
