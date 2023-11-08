from flask import Blueprint
from .routes import routes

bp = Blueprint('api', __name__)


routes(bp)
