from flask import Blueprint
from webapp_napilinux.api.routes import routes

bp = Blueprint('api', __name__)


routes(bp)
