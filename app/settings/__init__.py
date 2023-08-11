from flask import Blueprint
from app.settings.routes import routes

bp = Blueprint('settings', __name__)


routes(bp)
