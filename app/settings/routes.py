import subprocess

import time
from os import path, popen

from flask_login import login_required
from werkzeug.security import safe_join

from app.forms.network import NetworkForm
from app.forms.sensors import LoraConfigForm

from flask import render_template, flash, current_app, request, redirect, url_for, jsonify, session

from app.utils import (sys_uptime, sys_date, sys_ram, sys_cpu_avg, sys_disk, sys_wired_network_config, \
                       SysConfig, sys_service_restart, sys_soft_reset, db_size, db_clean, sys_auto_timezone, sys_reboot, sys_poweroff, \
                       ModemControl)


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

        # Deleting data in the 'wal' and 'date' folders, influxdb2 databases
        db_cln = request.args.get('dbclean')

        if request.method == 'GET' and db_cln == 'y':
            db_clean()
            return redirect(request.referrer)

        # Automatic set timezone after click in the button and if internet as exist
        tz_auto = request.args.get('tzauto')

        if request.method == 'GET' and tz_auto == 'y':
            sys_auto_timezone()
            return redirect(request.referrer)

        # System reboot
        reboot = request.args.get('reboot')

        if request.method == 'GET' and reboot == 'y':
            sys_soft_reset()
            sys_reboot()
            return redirect(request.referrer)

        # System poweroff
        poweroff = request.args.get('poweroff')

        if request.method == 'GET' and poweroff == 'y':
            sys_poweroff()
            return redirect(request.referrer)

        # System overlay reset
        soft_reset = request.args.get('soft_reset')

        if request.method == 'GET' and soft_reset == 'y':
            sys_soft_reset()
            sys_reboot()
            return redirect(request.referrer)

        return render_template(
            'settings/index.html',
            uptime=uptime,
            date=date,
            ram=ram,
            cpu_avg=cpu_avg,
            disk=disk,
            service_status=service_status,
            db=db,
        )

    @bp.route('/lora', methods=['GET', 'POST'])
    @login_required
    def lora_settings():
        def findparam(_path, word):
            with open(_path, "r") as f:
                text = f.readlines()
                for line in text:
                    if line.startswith(word):
                        if line.find(word) != -1:
                            result = line.split('=', 1)[1]
                f.close()
            return result

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
            sys_service_restart('systemd-networkd')
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

    @bp.route("/init_connection_setup", methods=['POST'])
    @login_required
    def init_settings_form_handler():
        if request.method == 'POST':
            apn_info = request.form['apn_input']
            ip_info = int(request.form.get("ipvX"))
            user_info = request.form.get("user_input")
            password_info = request.form.get("password_input")

            conn_config_input = (apn_info, ip_info, user_info, password_info)
            if conn_config_input == (None, ip_info, None, None) or conn_config_input[0] == '':
                conn_config_input = ('internet', ip_info, '', '')

            session['modem_connection_config'] = conn_config_input

            modem = ModemControl()
            connection_status = modem.modem_add_connection(conn_config_input)
            session['current_bearer'] = connection_status

        return redirect(url_for('settings.modem_settings'))

    @bp.route("/switch", methods=['POST'])
    @login_required
    def modem_connection_switch_handler():
        modem = ModemControl()
        con_status = request.json
        state = con_status.get('status')

        if state:
            modem.modem_delete_connection()
        else:
            modem_connection_config = session.get('modem_connection_config',
                                                  (modem.modem_get_init_apn(), 4, '', ''))
            connection_status = modem.modem_add_connection(modem_connection_config)
            session['current_bearer'] = connection_status
        return redirect(url_for('settings.modem_settings'))

    '''
    @bp.route("/ussd_request", methods=['POST'])
    @login_required
    def modem_ussd_handler():
        modem = ModemControl()
        return redirect(url_for('settings.modem_settings'))
    '''

    @bp.route("/modem", methods=['GET', 'POST'])
    @login_required
    def modem_settings():
        """Основная функция, связанная с URL адресом /settings/modem.
        Возвращает информацию о модеме, ответы в интерактивном поле запросов и булеан Истина. Также
        возвращает информацию о подключении."""
        modem = ModemControl()
        show_modem = modem.getter()
        nw_form = NetworkForm()
        modem_code_status = modem.modem_check_state()

        # Потенциально может быть проблема с получением поля имени Name
        network = SysConfig('wireless')
        name_status = network.net_config_read('Name')
        ip_status = network.net_config_read('Address')
        gw_status = network.net_config_read('Gateway')
        dns_status = network.net_config_read('DNS')

        ussd_status = modem.modem_ussd_status()
        current_bearer = session.get('current_bearer', str())

        (modem_current_apn, modem_current_ipv,
         modem_current_user, modem_current_pass) = session.get('modem_connection_config',
                                                               (modem.modem_get_init_apn(), 4, '', ''))

        '''
        if '/org/freedesktop/ModemManager1/Bearer' in current_bearer:
            modem_cur_bearer_prop = modem.modem_get_current_bearer_properties(
                'Properties', current_bearer)
            modem_current_apn = modem_cur_bearer_prop['apn']
            if modem_current_apn == '':
                modem_current_apn = 'internet'

            modem_current_user = modem_cur_bearer_prop['user']
            modem_current_pass = modem_cur_bearer_prop['password']
        elif current_bearer == 'error' or current_bearer == 'Critical error':
            modem_current_apn = 'Something wrong happened'
        else:
            modem_current_apn = '[Default]'
        '''

        response = False
        if request.method == 'POST':

            input_request = request.form.get('input_form')

            if input_request == 'ussd_cancel':
                response = modem.modem_ussd_cancel()
            elif modem.modem_ussd_status() == 1:
                response = modem.modem_ussd_request(input_request)
            elif modem.modem_ussd_status() == 3:
                modem.modem_ussd_response(input_request)
                time.sleep(5)
                # Костыль, но работает. При желании можно изменить время задержки
                response = modem.modem_ussd_network_request()
            redirect(url_for('settings.modem_settings'))

        output_form = {'modem_status': modem_code_status,
                       'show_modem': show_modem,
                       'response': response,
                       'nw_form': nw_form,
                       'is_modem_settings': True,
                       'name_status': name_status,
                       'address_status': ip_status,
                       'gateway_status': gw_status,
                       'dns_status': dns_status,
                       'ussd_status': ussd_status,
                       'current_bearer': current_bearer,
                       'modem_current_apn': modem_current_apn,
                       'modem_current_ipv': modem_current_ipv,
                       'modem_current_user': modem_current_user,
                       'modem_current_password': modem_current_pass}

        return render_template("/settings/modem.html",
                               form=output_form)
