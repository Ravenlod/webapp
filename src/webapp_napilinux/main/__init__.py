from flask import Blueprint
from .routes import routes

bp = Blueprint('main', __name__)

routes(bp)

