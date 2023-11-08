from ..extensions import db
from wtforms import widgets
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        default='admin'
    )
    password = db.Column(
        db.String(120),
        nullable=False,
        info={
            'widget': widgets.PasswordInput()
        }
    )

    def __repr__(self):
        return '<User %r>' % self.username
