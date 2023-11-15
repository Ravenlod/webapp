from flask import Blueprint
from .routes import routes

bp = Blueprint('auth', __name__)

routes(bp)

