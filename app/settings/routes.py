import subprocess
from os import path, popen

from flask_login import login_required
from werkzeug.security import safe_join

from app.forms.network import NetworkForm
from app.forms.sensors import LoraConfigForm
from app.settings import bp
from flask import render_template, flash, current_app, request, redirect, url_for, jsonify

from app.utils import sys_uptime, sys_date, sys_ram, sys_cpu_avg, sys_disk, sys_network_config, \
    SysConfig, sys_service_restart, db_size, db_clean, sys_auto_timezone, sys_reboot, sys_poweroff


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
            status = subprocess.check_output(f"systemctl show -p ActiveState --value {name}", universal_newlines=True,
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

    # TODO: В html template сделать валидацию
    if request.method == 'POST':
        dhcp = request.form.get(nw_form.dhcp.name)
        ip = request.form.get(nw_form.ip.name)
        gw = request.form.get(nw_form.gw.name)
        dns = request.form.get(nw_form.dns.name)
        sys_network_config(dhcp, ip, gw, dns)
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
