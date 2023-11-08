from flask import Blueprint
from webapp_napilinux.sensors.routes import routes

bp = Blueprint('sensors', __name__)

routes(bp)
