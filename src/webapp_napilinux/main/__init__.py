from flask import Blueprint
from webapp_napilinux.main.routes import routes

bp = Blueprint('main', __name__)

routes(bp)

