from flask import Blueprint
from app.auth.routes import routes

bp = Blueprint('auth', __name__)

routes(bp)

