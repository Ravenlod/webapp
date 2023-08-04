from flask import Flask, render_template
from flask_migrate import Migrate
from flask_login import LoginManager

from config import Config
from app.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.url_map.strict_slashes = False

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

    @app.route('/health')
    def test_page():
        return 'OK'

    return app
