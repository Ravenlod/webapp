from flask import Blueprint
from app.sensors.routes import routes

bp = Blueprint('sensors', __name__)

routes(bp)
