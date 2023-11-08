import glob
import os

from flask_login import current_user
# from app.main import bp
from flask import render_template, current_app, redirect, url_for
from werkzeug.security import safe_join

from ..utils import ModemControl


def routes(bp):
    @bp.route("/", methods=['GET'])
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        else:
            sensors_list = []
            current_directory = os.path.dirname(__file__)
            parent_directory = os.path.dirname(current_directory) 
            for f in sorted(glob.glob("*.conf", root_dir=f"{parent_directory}/confs")):
                name = str(f).split(".")[0]
                active_path = safe_join(current_app.config['ACTIVE_FOLDER'], f"{name}.conf")
                active = os.path.exists(active_path)
                sensors_list.append((name, active))
            return render_template('index.html', sensors_list=sensors_list, name=current_user.username)