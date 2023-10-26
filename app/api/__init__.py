from flask import Blueprint
from app.api.routes import routes

bp = Blueprint('api', __name__)


routes(bp)
