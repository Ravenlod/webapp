from wtforms import Form, BooleanField, StringField
from wtforms.validators import InputRequired, DataRequired, IPAddress


class NetworkForm(Form):
    dhcp = BooleanField('DHCP', validators=[DataRequired(), ])
    ip = StringField('IP', validators=[InputRequired(), IPAddress(message='Укажите ip!')])
    gw = StringField('Шлюз', validators=[InputRequired(), IPAddress(message='Укажите шлюз!')])
    dns = StringField('DNS', validators=[InputRequired(), IPAddress(message='Укажите DNS!')])
