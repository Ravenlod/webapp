from flask import Blueprint
from app.main.routes import routes

bp = Blueprint('main', __name__)

routes(bp)

