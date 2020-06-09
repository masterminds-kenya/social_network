from flask import current_app as app
from functools import wraps
from flask_login import current_user
from .model_db import User, Insight, Audience, Post, Campaign
import json


def mod_lookup(mod):
    """ Associate to the appropriate Model, or raise error if 'mod' is not an expected value """
    if not isinstance(mod, str):
        raise TypeError("Expected a string input. ")
    lookup = {'insight': Insight, 'audience': Audience, 'post': Post, 'campaign': Campaign}
    # 'onlinefollowers': OnlineFollowers,
    lookup.update({role: User for role in User.ROLES})
    Model = lookup.get(mod, None)
    if not Model:
        raise ValueError("That is not a valid url path. ")
    return Model


def prep_ig_decide(data):
    """ Some needed changes to prepare for the user to select amongst various Instagram accounts and data. """
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
    """ This decorator will allow use to limit access to routes based on user role. """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in role:
                return app.login_manager.unauthorized()
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


def admin_required(role=['admin']):
    """ This decorator will limit access to admin only """
    # staff_required(role=role)
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in role:
                return app.login_manager.unauthorized()
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


def self_or_staff_required(role=['admin', 'manager'], user=current_user):
    """ This decorator limits access to staff or if the resource belongs to the current_user. """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in role:
                return app.login_manager.unauthorized()
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper
