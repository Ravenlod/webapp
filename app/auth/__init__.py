from flask import Blueprint

bp: Blueprint = Blueprint('auth', __name__)

from app.auth import routes
