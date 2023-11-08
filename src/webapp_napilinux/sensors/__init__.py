from flask import Blueprint
from .routes import routes

bp = Blueprint('sensors', __name__)

routes(bp)
