from wtforms import Form, validators, PasswordField
from wtforms_sqlalchemy import ModelForm

from app.models.user import User


class UserLoginForm(ModelForm):
    class Meta:
        model = User


class ChangePasswordForm(Form):
    old_password = PasswordField('Old Password', [validators.DataRequired()])
    new_password = PasswordField('New Password', [validators.DataRequired(), validators.Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', [validators.EqualTo('new_password', message='Passwords must match')])
