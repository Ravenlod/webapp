from flask_login import login_required

from app.charts import bp
from flask import render_template

import socket
import fcntl
import struct


def get_local_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', bytes(ifname[:15], 'utf-8'))
    )[20:24])


@bp.route("/", methods=['GET'])
@login_required
def index():
    try:
        local_ip = get_local_ip_address('end0')
    except OSError:
        local_ip = '127.0.0.1'

    return render_template('charts/index.html', local_ip=local_ip)
