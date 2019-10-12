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


class User(db.Model):
    """Data model for user accounts."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=False, unique=True, nullable=False)
    email = db.Column(db.String(80), index=True, unique=True, nullable=False)
    created = db.Column(db.DateTime, index=False, unique=False, nullable=False)
    bio = db.Column(db.Text, index=False, unique=False, nullable=True)
    admin = db.Column(db.Boolean, index=False, unique=False, nullable=False)

    def __repr__(self):
        return '<User {}>'.format(self.username)


def create(data, Model=User):
    model = Model(created=dt.now(), **data)
    db.session.add(model)
    db.session.commit()
    return from_sql(model)


def read(id, Model=User):
    result = Model.query.get(id)
    if not result:
        return None
    return from_sql(result)


def update(data, id, Model=User):
    model = Model.query.get(id)
    for k, v in data.items():
        setattr(model, k, v)
    db.session.commit()
    return from_sql(model)


def delete(id, Model=User):
    Model.query.filter_by(id=id).delete()
    db.session.commit()


def list():
    query = (User.query.order_by(User.username))
    users = query.all()
    return users


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
