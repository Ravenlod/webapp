from flask import Blueprint
from webapp_napilinux.charts.routes import routes

bp = Blueprint('charts', __name__)

routes(bp)