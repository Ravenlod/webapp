import os
import secrets
from datetime import timedelta

secret_key = secrets.token_hex(16)
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = secret_key
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=40)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///' + os.path.join(basedir, 'webapp.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # MAX_CONTENT_LENGTH = 15360
    UPLOAD_EXTENSIONS = ['.conf']
    UPLOAD_FOLDER = os.path.join(basedir, 'confs/')
    ACTIVE_FOLDER = "/data/active/"
    LORABRIDGE_CFG = "/etc/lorabridge/lorabridge.conf"
    SESSION_COOKIE_NAME = "nnz_session"
    WEB_VERSION = "0.2.2"
    # TODO: В будущем парсить версии из файла swupdate
    SW_VERSION = "v.0.0.2-beta13"
    HW_VERSION = "rev3.3-FS-C1"
    IsModemAvailable = False
# print(basedir)
