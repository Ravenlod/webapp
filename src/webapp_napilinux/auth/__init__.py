from flask import Blueprint
from webapp_napilinux.auth.routes import routes

bp = Blueprint('auth', __name__)

routes(bp)

