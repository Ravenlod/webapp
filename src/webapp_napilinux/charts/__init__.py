from flask import Blueprint
from .routes import routes

bp = Blueprint('charts', __name__)

routes(bp)