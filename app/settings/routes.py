import subprocess
import json
import time
from os import path, popen

from flask_login import login_required
from werkzeug.security import safe_join
from pydbus import SystemBus
from gi.repository import GLib

from app.forms.network import NetworkForm
from app.forms.sensors import LoraConfigForm

from flask import render_template, flash, current_app, request, redirect, url_for, jsonify, session

from app.utils import sys_uptime, sys_date, sys_ram, sys_cpu_avg, sys_disk, sys_wired_network_config, \
    SysConfig, sys_service_restart, db_size, db_clean, sys_auto_timezone, sys_reboot, sys_poweroff, \
    sys_wireless_network_config, sys_manage_ip_route, sys_wireless_config_clear


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
            sys_reboot()
            return redirect(request.referrer)

        # System poweroff
        poweroff = request.args.get('poweroff')

        if request.method == 'GET' and poweroff == 'y':
            sys_poweroff()
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
        # TODO: получать статус из файла конфигурации
        network = SysConfig()
        dhcp_status = network.net_config_read('DHCP')
        ip_status = network.net_config_read('Address')
        gw_status = network.net_config_read('Gateway')
        dns_status = network.net_config_read('DNS')

        #  TODO: В html template сделать валидацию
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
            ip_info = request.form.get("ipvX")
            user_info = request.form.get("user_input")
            password_info = request.form.get("password_input")
            conn_config_input = (apn_info, ip_info, user_info, password_info)

            if conn_config_input == (None,) * 4:
                conn_config_input = ('internet', 4, '', '')
            modem = ModemControl()

            modem.modem_add_connection(conn_config_input)
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
            modem.modem_add_connection(('internet', 4, '', ''))
        return redirect(url_for('settings.modem_settings'))

    @bp.route("/ussd_request", methods=['POST'])
    @login_required
    def modem_ussd_handler():
        modem = ModemControl()
        return redirect(url_for('settings.modem_settings'))

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

        else:
            response = False
        return render_template("/settings/modem.html",
                               modem_status=modem_code_status,
                               show_modem=show_modem,
                               response=response,
                               is_modem_settings=True,
                               nw_form=nw_form,
                               name_status=name_status,
                               address_status=ip_status,
                               gateway_status=gw_status,
                               dns_status=dns_status,
                               ussd_status=ussd_status)

    class ModemControl:

        current_bearer = str()
        current_name = str()

        def modem_check_state(self):
            try:
                obj_current_modem = self.modem_current()
                modem_state = obj_current_modem['org.freedesktop.DBus.Properties'].Get(
                    'org.freedesktop.ModemManager1.Modem', 'State')
                return modem_state
            except:
                return 'Modem is missing'
        def modem_add_connection_nm(self):
            bus = SystemBus()
            nm = bus.get("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager")
            modem_path = self.modem_current_nm()
            nm.AddAndActivateConnection({'connection': {'id': GLib.Variant.new_string('modem'),
                                                        'type': GLib.Variant.new_string('gsm')},
                                         'gsm': {'apn': GLib.Variant.new_string('internet')}},
                                        modem_path, '/')
            # Detect all modem in system

        def modem_add_connection(self, config_input: tuple[str, int, str, str]):
            bus = SystemBus()
            obj_current_modem = self.modem_current()

            ports = obj_current_modem['org.freedesktop.DBus.Properties'].Get('org.freedesktop.ModemManager1.Modem',
                                                                             'Ports')
            simple_connect = obj_current_modem['org.freedesktop.ModemManager1.Modem.Simple']
            bearer_path = simple_connect.Connect({'apn': GLib.Variant.new_string(config_input[0]),
                                                  'ip-type': GLib.Variant.new_int32(int(config_input[1])),
                                                  'user': GLib.Variant.new_string(config_input[2]),
                                                  'password': GLib.Variant.new_string(config_input[3])})
            obj_current_modem['org.freedesktop.ModemManager1.Modem'].Enable('true')
            self.current_bearer = bus.get("org.freedesktop.ModemManager1", bearer_path)
            ip_dict = self.current_bearer['org.freedesktop.DBus.Properties'].Get('org.freedesktop.ModemManager1.Bearer',
                                                                                 'Ip4Config')
            self.current_name = [port[0] for port in ports if "ww" in port[0]][0]
            # port[0] возвращает список из одного элемента

            config_input = (self.current_name, ip_dict['address'], ip_dict['gateway'],
                            (ip_dict['dns1'], ip_dict['dns2']))
            # TODO Потенциальная ошибка, если DNS будет один экземпляр
            sys_wireless_network_config(config_input)
            sys_service_restart('systemd-networkd')
            e = sys_manage_ip_route(self.current_name, 500)
            return self.current_name

        def modem_delete_connection(self):
            bus = SystemBus()
            obj_current_modem = self.modem_current()
            ports = obj_current_modem['org.freedesktop.DBus.Properties'].Get('org.freedesktop.ModemManager1.Modem',
                                                                             'Ports')
            self.current_name = [port[0] for port in ports if "wwp" in port[0]][0]
            simple_connect = obj_current_modem['org.freedesktop.ModemManager1.Modem.Simple']

            e = sys_manage_ip_route(self.current_name, 500, "delete")
            simple_connect.Disconnect('/')
            sys_wireless_config_clear()
            sys_service_restart('systemd-networkd')

            # obj_current_modem['org.freedesktop.ModemManager1.Modem'].Enable('false')
            return self.current_name

        @staticmethod
        def modem_current():
            bus = SystemBus()
            try:
                # Root object
                obj_root = bus.get('.ModemManager1', '/org/freedesktop/ModemManager1')
                # Modem
                obj_current_modem = bus.get(
                    '.ModemManager1',
                    list(
                        obj_root['org.freedesktop.DBus.ObjectManager'].GetManagedObjects()
                    )
                        # last connected modem
                    [-1]
                )
                return obj_current_modem
            except:
                return False

        @staticmethod
        def modem_system_scan():
            bus = SystemBus()
            try:
                # Root object
                obj_root = bus.get('.ModemManager1', '/org/freedesktop/ModemManager1')
                obj_root.ScanDevices()
                return True
            except:
                print('Modem not found')
                return False

        @staticmethod
        def modem_current_nm():
            try:
                bus = SystemBus()
                nm = bus.get("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager")
                devices = nm.GetDevices()
                for device_path in devices:
                    device = bus.get("org.freedesktop.NetworkManager", device_path)
                    if device.DeviceType == 8:
                        return device_path
                return False
            except:
                return False

        def modem_ussd_request(self, ussd_code):
            """Метод, который позволяет посылать USSD запросы. Не может отменять текущую сессию запросов."""
            try:
                obj_current_modem = self.modem_current()
                # USSD session
                ussd = obj_current_modem['org.freedesktop.ModemManager1.Modem.Modem3gpp.Ussd']
                ussd_request = str(ussd.Initiate(ussd_code))
                return ussd_request
            except:
                print('Modem not found')
                return False

        def modem_ussd_status(self):
            """Метод, возвращающий код состояния сессии USSD. MM_MODEM_3GPP_USSD_SESSION_STATE_UNKNOWN = 0
 - Unknown state;
MM_MODEM_3GPP_USSD_SESSION_STATE_IDLE = 1
 - No active session;
MM_MODEM_3GPP_USSD_SESSION_STATE_ACTIVE = 2
 - A session is active and the mobile is waiting for a response;
MM_MODEM_3GPP_USSD_SESSION_STATE_USER_RESPONSE = 3
 - The network is waiting for the client's response."""
            try:
                obj_current_modem = self.modem_current()
                ussd_status = obj_current_modem['org.freedesktop.DBus.Properties'].Get(
                    'org.freedesktop.ModemManager1.Modem.Modem3gpp.Ussd', 'State')
                return ussd_status
            except:
                return False

        def modem_ussd_response(self, ussd_code):
            obj_current_modem = self.modem_current()
            ussd = obj_current_modem['org.freedesktop.ModemManager1.Modem.Modem3gpp.Ussd']
            ussd.Respond(ussd_code)

        def modem_ussd_network_request(self):
            obj_current_modem = self.modem_current()
            ussd_response = obj_current_modem['org.freedesktop.DBus.Properties'].Get(
                'org.freedesktop.ModemManager1.Modem.Modem3gpp.Ussd',
                'NetworkRequest')
            return ussd_response

        def modem_ussd_cancel(self):
            try:
                obj_current_modem = self.modem_current()
                # USSD session
                ussd = obj_current_modem['org.freedesktop.ModemManager1.Modem.Modem3gpp.Ussd']
                ussd.Cancel()
                return 'OK'
            except:
                return 'Unknown Error'

        def modem_apn_set(self, apn_input):
            """ Метод, который позволяет настроить APN для текущего профиля"""
            try:
                obj_current_modem = self.modem_current()
                apn_set = obj_current_modem['org.freedesktop.ModemManager1.Modem.Modem3gpp.ProfileManager']
                apn_set.Set({'profile-id': GLib.Variant.new_int32(1), 'apn': GLib.Variant.new_string(str(apn_input))})
                response = apn_set.List()
                return response

            except:
                return 'False'

        def modem_info(self):
            # DBUS lib tutorial https://github.com/LEW21/pydbus/blob/master/doc/tutorial.rst
            try:
                obj_current_modem = self.modem_current()
                current_modem = obj_current_modem['org.freedesktop.ModemManager1.Modem']

                # Values
                info = dict()

                if any(slot != '/' for slot in current_modem.SimSlots):
                    bus = SystemBus()

                    # SIM card
                    obj_sim = bus.get('.ModemManager1', current_modem.Sim)
                    current_sim = obj_sim['org.freedesktop.ModemManager1.Sim']

                    info['manufacturer'] = str(current_modem.Manufacturer)
                    info['model'] = str(current_modem.Model)
                    info['operator'] = str(current_sim.OperatorName)

                    # Modem3gpp
                    modem3gpp = obj_current_modem['org.freedesktop.ModemManager1.Modem.Modem3gpp']

                    info['imei'] = str(modem3gpp.Imei)

                    info['active'] = bool(current_sim.Active)
                    info['signal'] = int(current_modem.SignalQuality[0])
                    info['simId'] = str(current_sim.SimIdentifier)
                    info['imsi'] = str(current_sim.Imsi)

                    # New info
                    info['primary port'] = str(current_modem.PrimaryPort)

                else:
                    info['sim'] = bool(False)

                return info
            except:
                print('Modem not found')
                return False

        def getter(self):
            """ Метод для безопасного возврата информации о модеме """
            return self.modem_info()
