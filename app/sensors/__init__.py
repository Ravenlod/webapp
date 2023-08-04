from flask import Blueprint

bp = Blueprint('sensors', __name__)

from app.sensors import routes
