from flask import Blueprint
from app.charts.routes import routes

bp = Blueprint('charts', __name__)

routes(bp)