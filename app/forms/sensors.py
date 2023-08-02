from wtforms import Form, validators, StringField, BooleanField, IntegerField, SelectField, TextAreaField
from wtforms.validators import DataRequired


class SensorsSettingsForm(Form):
    sensor = StringField("Название датчика",
                         validators=[DataRequired("Это поле необходимо заполнить"), validators.Length(max=30)])
    data_source = StringField('Источник данных (tcp, консоль)',
                              validators=[DataRequired("Это поле необходимо заполнить"), validators.Length(max=140)])
    period = IntegerField('Период опроса, мс', validators=[DataRequired(), validators.number_range(10, 3600000)],
                          default=100)
    modbus_slave_id = IntegerField('Modbus Slave ID', validators=[DataRequired(), validators.number_range(1, 247)],
                                   default=1)
    timeout = IntegerField('Таймаут опроса датчика, с', validators=[DataRequired(), validators.number_range(1, 60)],
                           default=1)
    active = BooleanField('Опрашивать датчик', default=False)


class LoraConfigForm(Form):
    appkey = StringField("AppKey",
                         validators=[DataRequired("Это поле необходимо заполнить"), validators.Length(min=32, max=32)])
    mqtttopics = StringField("mqtt topics",
                             validators=[DataRequired("Это поле необходимо заполнить"), validators.Length(max=50)])
    # loraregion = StringField("LoRa region",
    #                          validators=[DataRequired("Это поле необходимо заполнить"),
    #                                      validators.Length(min=5, max=5)])

    deviceAddress = StringField("Device address",
                                validators=[DataRequired("Это поле необходимо заполнить"), validators.Length(max=32)])
    lorafport = IntegerField('FPort', validators=[DataRequired("Это поле необходимо заполнить"),
                                                  validators.number_range(1, 233)], default=1)
    loraregion = SelectField("LoRa region", choices=[('EU868', 'EU868'), ('RU864', 'RU864'), ('IN865', 'IN865'),
                                                     ('US915', 'US915'), ('AU915', 'AU915'), ('KR920', 'KR920')])
    # submit = SubmitField("asd")


class SensorsTextConf(Form):
    conf_text_area = TextAreaField("Файл конфигурации датчика", validators=[DataRequired()])


class SensorAddConf(Form):
    sensor_name = StringField(
        "Название датчика",
        validators=[DataRequired(), validators.Length(min=2, max=20)]
    )
    conf_text = TextAreaField(
        "Конфигурация",
        validators=[DataRequired()]
    )
