import json

from flask import Flask, render_template, Response
from flask_migrate import Migrate
from flask_login import LoginManager

from config import Config
from app.extensions import db
from app.utils import ModemControl
from werkzeug.exceptions import HTTPException


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.url_map.strict_slashes = False

    # if is_modem_available:
    #     with open()
    # Config.IsModemAvailable = modem.modem_system_scan()
    # print(bool(modem.modem_current()))

    # Initialize Flask extensions here
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our auth table, use it in the query for the auth
        return User.query.get(int(user_id))

    # Register blueprints here
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.settings import bp as settings_bp
    app.register_blueprint(settings_bp, url_prefix='/settings')

    from app.charts import bp as charts_bp
    app.register_blueprint(charts_bp, url_prefix='/charts')

    from app.sensors import bp as sensors_bp
    app.register_blueprint(sensors_bp, url_prefix='/sensors')


    #Error Handlers
    #app.register_error_handler(500, 'errors/internal_error.html')
    #app.register_error_handler(404, 'errors/page_not_found.html')

    # @app.errorhandler(Exception)
    # def handle_exception(e):
    #     if not isinstance(e, HTTPException):
    #         return render_template('errors/internal_error.html', e=e), 500
    # @app.errorhandler(404)
    # def page_not_found(e):
    #         return render_template('errors/page_not_found.html'), 404

    @app.route('/health')
    def test_page():
        return 'OK'

    @app.route('/connected_device_handler')
    def device_handler():
        modem = ModemControl()
        is_modem_available = bool(modem.modem_current())
        # app.config['IsModemAvailable'] = is_modem_available
        if is_modem_available:
            data = {"device-type": "1"}
        else:
            data = {"device-type": "-1"}
        json_data = json.dumps(data)
        return Response(json_data, content_type="application/json")

    return app
