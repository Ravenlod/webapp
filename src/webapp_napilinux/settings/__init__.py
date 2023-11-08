from flask import Blueprint
from .routes import routes

bp = Blueprint('settings', __name__)


routes(bp)
