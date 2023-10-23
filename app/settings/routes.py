import os.path
import subprocess

import time
from os import path, popen

from flask_login import login_required
from werkzeug.security import safe_join

from app.forms.network import NetworkForm
from app.forms.sensors import LoraConfigForm

from flask import render_template, flash, current_app, request, redirect, url_for, jsonify, session, Response, abort

from app.utils import (sys_uptime, sys_date, sys_ram, sys_cpu_avg, sys_disk, sys_wired_network_config, SysConfig,
                       sys_service_manage, sys_soft_reset, db_size, db_clean, sys_auto_timezone, sys_reboot,
                       sys_poweroff, ModemControl, findparam, generate_event)


def routes(bp):
    @bp.route("/", methods=['GET'])
    @login_required
    def index():
        uptime = str(sys_uptime())
        date = str(sys_date())
        ram = str(sys_ram())
        cpu_avg = str(sys_cpu_avg())
        disk = str(sys_disk())
        db = str(db_size())

        
        

        return render_template(
            'settings/index.html',
            uptime=uptime,
            date=date,
            ram=ram,
            cpu_avg=cpu_avg,
            disk=disk,
            db=db,
        )

    @bp.route("/service-list", methods=["GET"])
    @login_required
    def service_list():
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
                status = subprocess.check_output(f"systemctl show -p ActiveState --value {name}",
                                                 universal_newlines=True,
                                                 shell=True)
                status = str(status).split("\n")[0]
                service_status.append((name, status))
        else:
            flash('Тут нет Systemd 😱')

        return jsonify({"data": service_status})

    @bp.route("/create", methods=['POST'])
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

    @bp.route("/update", methods=['PUT'])
    @login_required

    def update_handler():
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
                pass
            elif config['name'] == "service-preset":
                pass
        
        return jsonify({"message": "Resource updated successfully"}), 200
    
    @bp.route('/lora', methods=['GET', 'POST'])
    @login_required
    def lora_settings():

        def replaceparam(_path, key_to_replace, word):
            with open(_path, "r+") as lora_cfg:
                # Read the file line by line
                lines = lora_cfg.readlines()

                # Loop through the lines and find the key to replace
                for i, line in enumerate(lines):
                    if line.startswith(key_to_replace + "="):
                        # If the key is found, replace its value
                        lines[i] = key_to_replace + "=" + word + "\n"
                        break

                # Write the modified lines back to the file
                lora_cfg.seek(0)
                lora_cfg.writelines(lines)
                lora_cfg.close()

        form = LoraConfigForm()
        file = safe_join(current_app.config["LORABRIDGE_CFG"])
        loraappkey = findparam(file, 'appkey')
        mqtttopic = findparam(file, 'mqttTopics')
        lorafport = findparam(file, 'fport')
        deviceAddress = findparam(file, 'deviceAddress')
        loraregions = findparam(file, 'region').split()[0]
        choise_region = form.loraregion.choices
        sw_reset = request.args.get('sw-reset')
        if request.method == 'POST':
            loraappkeynew = request.form.get(form.appkey.name)
            replaceparam(file, 'appkey', loraappkeynew)
            mqtttopicnew = request.form.get(form.mqtttopics.name)
            replaceparam(file, 'mqttTopics', mqtttopicnew)
            loraregionnew = request.form.get(form.loraregion.name)
            replaceparam(file, 'region', loraregionnew)
            lora_fport_new = request.form.get(form.lorafport.name)
            replaceparam(file, 'fport', lora_fport_new)
            deviceAddress_new = request.form.get(form.deviceAddress.name)
            replaceparam(file, 'deviceAddress', deviceAddress_new)
            # flash('Сохранено!')
            return redirect(request.referrer)
        if request.method == 'GET' and sw_reset == 'y':
            lbr_stop = [f"sudo systemctl stop lorabridge.service"]
            lbr_start = [f"sudo systemctl start lorabridge.service"]
            try:
                subprocess.check_output(lbr_stop, universal_newlines=True, shell=True)
                popen("/usr/bin/lorabridge --help").read()
                subprocess.check_output(lbr_start, universal_newlines=True, shell=True)
            except subprocess.CalledProcessError:
                flash("Недостаточно системных прав!")
                pass
            return redirect(request.referrer)

        return render_template(
            'settings/lora.html',
            form=form,
            loraappkey=loraappkey,
            loraregions=loraregions,
            mqtttopic=mqtttopic,
            choise_region=choise_region,
            sw_reset=sw_reset,
            lorafport=lorafport,
            deviceAddress=deviceAddress
        )

    @bp.route("/network", methods=['GET', 'POST'])
    @login_required
    def network_settings():
        nw_form = NetworkForm()
        # TODO: получать статус из файла конфигурации?
        network = SysConfig()
        dhcp_status = network.net_config_read('DHCP')
        ip_status = network.net_config_read('Address')
        gw_status = network.net_config_read('Gateway')
        dns_status = network.net_config_read('DNS')

        if request.method == 'POST':
            config_input = (request.form.get(nw_form.dhcp.name),
                            request.form.get(nw_form.ip.name),
                            request.form.get(nw_form.gw.name),
                            request.form.get(nw_form.dns.name)
                            )
            # DHCP, Ip, Gateway, DNS
            sys_wired_network_config(config_input)
            sys_service_manage('systemd-networkd')
            return redirect(url_for('settings.network_settings'))
        return render_template(
            'settings/network.html',
            nw_form=nw_form,
            dhcp_status=dhcp_status,
            ip=ip_status,
            gw=gw_status,
            dns=dns_status,
            ip_current=network.ip_current()
        )

    @bp.route("/firmware", methods=['GET', 'POST'])
    @login_required
    def firmware_settings():

        if request.method == "POST":
            firmware_file = request.files['firmware']
            # return Response(update_firmware(firmware_file), mimetype='text/event-stream')
            temp_file_path = path.join('/tmp', firmware_file.filename)
            firmware_file.save(temp_file_path)

            cmd = ['swupdate', '-v', temp_file_path]
            output = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]

            return jsonify({'message': 'Firmware update complete', 'output': output.decode('utf-8')})

        return render_template(
            'settings/firmware.html'
        )

    @bp.route('/sse')
    @login_required
    def sse():
        return Response(generate_event(), content_type='text/event-stream')


    @bp.route("/ussd_request", methods=['GET'])
    @login_required
    def modem_ussd_handler():
        modem = ModemControl()
        modem_ussd_status_user_friendly = ('UNKNOWN', 'IDLE', 'ACTIVE', 'USER RESPONSE')

        if request.method == "GET":
            ussd_status = modem.modem_ussd_status()            
            return_data = {'ussd_status': modem_ussd_status_user_friendly[ussd_status]}
        
            return jsonify(return_data), 200

    @bp.route("/modem")
    @login_required
    def modem_settings():
        """Основная функция, связанная с URL адресом /settings/modem.
        Возвращает информацию о модеме, ответы в интерактивном поле запросов и булеан Истина. Также
        возвращает информацию о подключении."""
        modem = ModemControl()
        show_modem = modem.getter()
        output_form = {
            'show_modem': show_modem     
        }
        return render_template("/settings/modem.html",
                               form=output_form)

    @bp.route("/overlays", methods=['GET', 'POST'])
    @login_required
    def modem_overlays_control():
        feedback_value = str()
        file_path = "/boot/uEnv.txt"
        overlays_path = "/boot/overlays"
        mutual_exclusive_overlays = (('UART0', 'SPI0'), ('UART1', 'I2C0', 'SPI2'), ('SPI2', 'UART2'),
                                     ('GPIO3', 'SPI1', 'UART3'), ('GPIO4', 'UART4'))
        current_overlays = list()
        overlays_uart_groups = {"Interface_" + str(key): list() for key in range(len(mutual_exclusive_overlays))}
        overlays_ungrouped = list()
        unfiltered_overlays_list = list()
        switch_group_ungroup = False
        rk3308_overlays = list()
        dir_value = os.listdir(overlays_path)
        for file in dir_value:
            filename, ext = os.path.splitext(file)
            unfiltered_overlays_list.append(filename)
            if 'rk3308' in filename.lower():
                rk3308_overlays.append(filename)
                for group_index, group_tuple in enumerate(mutual_exclusive_overlays):
                    for exclusive in group_tuple:
                        if exclusive.lower() in filename.lower():
                            overlays_uart_groups["Interface_" + str(group_index)].append(filename)
                            switch_group_ungroup = True
                if not switch_group_ungroup:
                    overlays_ungrouped.append(filename)
                switch_group_ungroup = False

        if request.method == 'POST':
            row_index = int()
            switch = False
            with (open(file_path, 'r') as uboot_config):
                lines = uboot_config.readlines()
                for line in lines:
                    if 'overlays=' in line:
                        cut = line[len('overlays='):]
                        break
                current_overlays_change = cut.split(' ')
                current_overlays_change[-1] = current_overlays_change[-1][:-1]
                print(current_overlays_change)

                for key, value in overlays_uart_groups.items():
                    check = request.form.get(key)
                    if check is not None:

                        for check_element in value:
                            for change_index, test_element in enumerate(current_overlays_change):
                                if check_element == test_element:
                                    current_overlays_change[change_index] = check
                                    switch = True
                                    break
                        if not switch:
                            current_overlays_change.insert(0, check)
                        elif switch:
                            switch = False
                    else:
                        for check_element in value:
                            for change_index, test_element in enumerate(current_overlays_change):
                                if check_element == test_element:
                                    current_overlays_change.pop(change_index)

                switch = False
                for item in overlays_ungrouped:
                    check = request.form.get(item)

                    if check is not None:
                        print(check)
                        for change_index, test_element in enumerate(current_overlays_change):
                            if check == test_element:
                                switch = True
                                break
                        if not switch:
                            current_overlays_change.insert(0, check)
                        elif switch:
                            switch = False
                    else:
                        for change_index, test_element in enumerate(current_overlays_change):
                            if item == test_element:
                                print('change')
                                print(change_index)
                                current_overlays_change.pop(change_index)
                for index_temp, line in enumerate(lines):
                    if 'overlays=' in line:
                        row_index = index_temp
                        break
                lines[row_index] = "overlays=" + " ".join(current_overlays_change) + '\n'
                print(lines[row_index])

            with open(file_path, 'w') as uboot_config:
                uboot_config.writelines(lines)

            return redirect(url_for('settings.modem_overlays_control'))

        if os.path.isfile(file_path):
            with open(file_path, "r") as uboot_config:

                lines = uboot_config.readlines()
                for line in lines:
                    if 'overlays=' in line:
                        cut = line[len('overlays='):]
                        break
                current_overlays = cut.split(' ')
                current_overlays[-1] = current_overlays[-1][:-1]
        else:
            feedback_value = "File doesn't exist"

        return render_template("/settings/overlays.html",
                               feedback_value=feedback_value,
                               overlays_list=overlays_uart_groups,
                               current_overlays=current_overlays,
                               rk3308_overlays=rk3308_overlays,
                               overlays_ungrouped=overlays_ungrouped,
                               unfiltered_overlays_list=unfiltered_overlays_list)
