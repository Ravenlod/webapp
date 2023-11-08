from flask import Blueprint
from webapp_napilinux.settings.routes import routes

bp = Blueprint('settings', __name__)


routes(bp)
