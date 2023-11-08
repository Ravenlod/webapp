import glob
import os

from flask_login import current_user
# from app.main import bp
from flask import render_template, current_app, redirect, url_for
from werkzeug.security import safe_join

from app.utils import ModemControl


def routes(bp):
    @bp.route("/", methods=['GET'])
    def index():
        modem = ModemControl()

        # modem_status = modem.modem_system_scan()
        # Config.IsModemAvailable = modem_status
        # print(modem_status)
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        else:
            sensors_list = []
            for f in reversed(sorted(glob.glob("confs/*.conf"), key=os.path.getmtime)):
                name = str(f).split("/")[1].split(".")[0]
                active_path = safe_join(current_app.config['ACTIVE_FOLDER'], f"{name}.conf")
                active = os.path.exists(active_path)
                sensors_list.append((name, active))
            return render_template('index.html', sensors_list=sensors_list, name=current_user.username)