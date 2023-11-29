import subprocess

import time
from os import path

from flask_login import login_required

from flask import flash, request, jsonify, session, Response, abort

from ..utils import (sys_service_manage, sys_soft_reset, db_clean, sys_auto_timezone, sys_reboot,
                    sys_poweroff, ModemControl, generate_modem_state, generate_index, generate_log)


def routes(bp):


    @bp.route('/settings/sse', methods=["GET"])
    @login_required
    def sse():
        target = request.args.get('target', 'default_value')
        if target == "modem":
            return Response(generate_modem_state(), content_type='text/event-stream')
        elif target == "index":
            return Response(generate_index(), content_type='text/event-stream')
        elif target == "update":
            file_path = request.args.get('path', 'none')
            return Response(generate_log(file_path), content_type='text/event-stream')
        else: 
            return

    @bp.route("/settings/<string:module_name>", methods=["GET"])
    @login_required
    def module_handler(module_name):
        if module_name == "service-list":
            service_status = []

            if path.exists('/usr/bin/systemctl') or path.exists('/bin/systemctl') is True:
                service_list = [
                    'systemd-networkd',
                    'systemd-resolved',
                    'telegraf',
                    'lorabridge',
                    'mosquitto',
                    'grafana-server',
                    'influxdb',
                    'swupdate',
                ]
                service_installed = []

                # Check installed service status
                for i in service_list:
                    try:
                        name = str(i).split(".")[0]
                        subprocess.check_output(["systemctl", "cat", f"{name}"], stderr=subprocess.STDOUT)
                        service_installed.append(name)
                    except subprocess.CalledProcessError:
                        pass

                for s in service_installed:
                    name = str(s).split(".")[0]
                    is_active = subprocess.check_output(f"systemctl show -p ActiveState --value {name}",
                                                    universal_newlines=True,
                                                    shell=True)
                    is_active = str(is_active).split("\n")[0]
                    is_enabled = subprocess.check_output(f"systemctl show -p UnitFileState --value {name}",
                                                    universal_newlines=True,
                                                    shell=True)
                    is_enabled = str(is_enabled).split("\n")[0]
                    service_status.append((name, is_active, is_enabled))
                    return_data = {"data": service_status}
            else:
                flash('Тут нет Systemd 😱')

        elif module_name == "ussd-request":
            modem = ModemControl()
            modem_ussd_status_user_friendly = ('UNKNOWN', 'IDLE', 'ACTIVE', 'USER RESPONSE')

            ussd_status = modem.modem_ussd_status()            
            return_data = {'ussd_status': modem_ussd_status_user_friendly[ussd_status]}

        else:
            abort(400)
        return jsonify(return_data)


    @bp.route("/settings/create", methods=['POST'])
    @login_required
    def create_handler():
        config = request.json
        if not config or not 'name' in config:
            abort(400)
        else:
            if config['name'] == "ussd-request":
                modem = ModemControl()
                modem_ussd_status_user_friendly = ('UNKNOWN', 'IDLE', 'ACTIVE', 'USER RESPONSE')
                response = False
                input_request = request.json

                if input_request["data"] == 'ussd_cancel':
                    response = modem.modem_ussd_cancel()
                elif modem.modem_ussd_status() == 1:
                    response = modem.modem_ussd_request(input_request["data"])
                elif modem.modem_ussd_status() == 3:
                    modem.modem_ussd_response(input_request["data"])

                    # Можно изменить время задержки
                    time.sleep(5)
                    response = modem.modem_ussd_network_request()

                ussd_status = modem.modem_ussd_status()
                return_data = {"response": response, 'ussd_status': modem_ussd_status_user_friendly[ussd_status]}

            elif config['name'] == "index-msg":
                if config['data'] == 'db-clean':
                    db_clean()
                    return_data = {"response": "DB Cleaned"}

                elif config['data'] == "tzauto":
                    sys_auto_timezone()
                    return_data = {"response": "Timezone set"}

                elif config['data'] == "reboot":
                    sys_reboot()
                    return_data = {"response": "Reboot confirmed"}

                elif config['data'] == "poweroff":
                    sys_poweroff()
                    return_data = {"response": "Poweroff confirmed"}

                elif config['data'] == "soft-reset":
                    sys_soft_reset()
                    sys_reboot()
                    return_data = {"response": "Soft reset confirmed"}

        return jsonify(return_data), 200

    @bp.route("/settings/update", methods=['PUT'])
    @login_required

    def update_handler():
        if request.json:
            config = request.json
            if not config or not 'name' in config:
                abort(400)
            else:
                if config['name'] == "connection-switch":
                    modem = ModemControl()
                    con_status = request.json
                    state = con_status.get('status')

                    if state:
                        modem.modem_delete_connection()
                    else:
                        modem_connection_config = session.get('modem_connection_config',
                                                            (modem.modem_get_init_apn(), 4, '', ''))
                        modem.modem_add_connection(modem_connection_config)

                elif config['name'] == "connection-form":
                    apn_info = config['apn']
                    ip_info = int(config['ip'])
                    user_info = config["user"]
                    password_info = config["password"]
                    conn_config_input = (apn_info, ip_info, user_info, password_info)

                    if conn_config_input == ("", ip_info, "", "") or conn_config_input[0] == '':
                        conn_config_input = ('internet', ip_info, '', '')

                    session['modem_connection_config'] = conn_config_input
                    modem = ModemControl()
                    modem.modem_add_connection(conn_config_input)

                elif config['name'] == "service-status":
                    if path.exists('/usr/bin/systemctl') or path.exists('/bin/systemctl') is True:
                        service_list = [
                            'systemd-networkd',
                            'systemd-resolved',
                            'telegraf',
                            'lorabridge',
                            'mosquitto',
                            'grafana-server',
                            'influxdb',
                            'swupdate',
                        ]
                        service_installed = []

                        # Check installed service status
                        for i in service_list:
                            try:
                                name = str(i).split(".")[0]
                                subprocess.check_output(["systemctl", "cat", f"{name}"], stderr=subprocess.STDOUT)
                                service_installed.append(name)
                            except subprocess.CalledProcessError:
                                pass
                                # return jsonify({"message": "Service not found"}), 404

                        if config['data'][1] == "Active":        
                            sys_service_manage(service_installed[int(config['data'][0])], "stop")
                        else:
                            sys_service_manage(service_installed[int(config['data'][0])], "start")

                elif config['name'] == "service-preset":
                    if path.exists('/usr/bin/systemctl') or path.exists('/bin/systemctl') is True:
                        service_list = [
                            'systemd-networkd',
                            'systemd-resolved',
                            'telegraf',
                            'lorabridge',
                            'mosquitto',
                            'grafana-server',
                            'influxdb',
                            'swupdate',
                        ]
                        service_installed = []

                        # Check installed service status
                        for i in service_list:
                            try:
                                name = str(i).split(".")[0]
                                subprocess.check_output(["systemctl", "cat", f"{name}"], stderr=subprocess.STDOUT)
                                service_installed.append(name)
                            except subprocess.CalledProcessError:
                                pass
                                # return jsonify({"message": "Service not found"}), 404

                        if config['data'][1] == "Enabled":        
                            sys_service_manage(service_installed[int(config['data'][0])], "disable")
                        else:
                            sys_service_manage(service_installed[int(config['data'][0])], "enable")
        elif 'file' in request.files:
            firmware_file = request.files['file']
            temp_file_path = path.join('/tmp', firmware_file.filename)
            firmware_file.save(temp_file_path)
            return jsonify({"file_path": temp_file_path}), 200
        return jsonify({"message": "Resource updated successfully"}), 200
