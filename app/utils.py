import subprocess
from os import popen, path, system
# from datetime import datetime

from flask import flash

ALLOWED_EXTENSIONS = {'conf'}


class SysConfig:
    netconfig = str()

    def __init__(self, connection_type="wired"):
        wired_netconfig = '/etc/systemd/network/20-wired.network'
        wireless_netconfig = '/etc/systemd/network/30-modem.network'

        if connection_type == "wired":
            self.netconfig = wired_netconfig
        elif connection_type == "wireless":
            self.netconfig = wireless_netconfig
        # TODO Не дописаны исключения

    def net_config_read(self, word):
        try:
            open(self.netconfig, "x")
        except FileExistsError:
            # flash("Что-то пошло не так")
            pass
        result = ''
        with open(self.netconfig, "r") as f:
            text = f.readlines()
            for line in text:
                if line.startswith(word):
                    if line.find(word) != -1:
                        result = line.split('=', 1)[1]
            f.close()
        return result

    def ip_current(self):
        net = popen(
            f'networkctl status | head -n8'
        ).read()
        return net


def sys_wireless_network_config(config_input):
    """config_input( str(Name), str(Address), str(Gateway), tuple(DNS) )"""
    config_path = '/etc/systemd/network/30-modem.network'
    with open(config_path, 'w') as f:
        row = ','.join(config_input[3])
        line1 = '[Match]\n'
        line2 = '\n'
        line3 = f'Name={config_input[0][0]}\n'
        line4 = '[Network]\n'
        line5 = '\n'
        line6 = f'Address={config_input[1]}\n'
        line7 = f'Gateway={config_input[2]}\n'
        line8 = f'DNS={row}\n'
        f.writelines([
            line1, line2, line3,
            line4, line5, line6,
            line7, line8,
        ])
        f.close()
    '''
        with open(config_path,"r") as f:
        text = f.read()
        f.close()
    return text
    '''


def sys_wired_network_config(config_input):
    """config_input(DHCP, Ip, Gateway, DNS)"""
    config_path = '/etc/systemd/network/20-wired.network'
    dhcp_param = bool(config_input[0])
    if dhcp_param:
        with open(config_path, 'w') as f:
            line1 = "[Match]\n"
            line2 = "Name=end0\n"
            line3 = "\n"
            line4 = "[Network]\n"
            line5 = "DHCP=ipv4\n"
            line6 = "LinkLocalAddressing=ipv4\n"
            line7 = "IPv6AcceptRA=no\n"
            line8 = "IPv4LLStartAddress=169.254.100.100\n"
            line9 = "\n"
            line10 = "[DHCP]\n"
            line11 = "RouteMetric=10\n"
            line12 = "ClientIdentifier=mac\n"
            f.writelines([
                line1, line2, line3,
                line4, line5, line6,
                line7, line8, line9,
                line10, line11, line12,
            ])
            f.close()
    else:
        with open(config_path, 'w') as f:
            line1 = "[Match]\n"
            line2 = "Name=end0\n"
            line3 = "\n"
            line4 = "[Network]\n"
            line5 = f"Address={config_input[1]}\n"
            line6 = f"Gateway={config_input[2]}\n"
            line7 = f"DNS={config_input[3]}\n"
            f.writelines([
                line1, line2, line3,
                line4, line5, line6,
                line7
            ])
            f.close()


def sys_auto_timezone():
    check_time = popen(
        'curl http://ip-api.com/line?fields=timezone'
    ).read()
    popen(
        f'timedatectl set-timezone {check_time}'
    )
    popen(
        'hwclock --systohc'
    )


def sys_reboot():
    system('systemctl reboot -i')


def sys_poweroff():
    system('systemctl poweroff -i')


def sys_disk():
    disk = popen(
        'df -h / | tail -1 | awk \'{print "Disk size: "$2"   Used: " $3"("$5")   Avail: " $4}\''
    ).read()
    return disk


def sys_cpu_avg():
    cpu_avg = popen(
        'awk \'{print "1 min: "$1 " / 5 min: "$2 " / 15 min: "$3}\' /proc/loadavg'
    ).read()
    return cpu_avg


def sys_ram():
    ram = popen("free -h").read()
    return ram


def db_size():
    try:
        db = popen("du -sh /home/root/.influxdbv2/ | awk \'{print $1}\'").read()
    except OSError:
        db = "size_error"
    return db


def db_clean():
    popen("rm -rf /home/root/.influxdbv2/engine/wal/*")
    popen("rm -rf /home/root/.influxdbv2/engine/data/*")
    sys_service_restart("influxdb")


def sys_uptime():
    uptime = popen(
        'awk \'{print int($1/86400)" days "int($1%86400/3600)":"int(($1%3600)/60)":"int($1%60)}\' /proc/uptime'
    ).read()
    return uptime


def sys_date():
    # now = datetime.now()
    # date = now.strftime("%d/%m/%Y %H:%M:%S")
    date = popen(
        'date +"%Y-%m-%d %H:%M:%S (%Z)"'
    ).read()
    return date


def sys_manage_ip_route(name: str, metric: int, change="add"):
    """Добавление в таблицу маршрутизации устройства с данной метрикой"""
    if change == 'add' or change == 'delete':
        change = [f"sudo ip route {change} default dev {name} metric {metric}"]
    else:
        return "Unknown command"
    try:
        subprocess.check_output(change, universal_newlines=True, shell=True)

    except subprocess.CalledProcessError:
        return "Недостаточно системных прав!"
        pass


def sys_service_restart(service):
    restart = [f"sudo systemctl restart {service}.service"]
    # stop = [f"sudo systemctl stop {service}.service"]
    # start = [f"sudo systemctl start {service}.service"]
    try:
        subprocess.check_output(restart, universal_newlines=True, shell=True)
        # subprocess.check_output(stop, universal_newlines=True, shell=True)
        # subprocess.check_output(start, universal_newlines=True, shell=True)
    except subprocess.CalledProcessError:
        flash("Недостаточно системных прав!")
        pass


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def update_firmware(firmware_file):
    temp_file_path = path.join('/tmp', firmware_file.filename)
    firmware_file.save(temp_file_path)

    cmd = ['swupdate', '-v', temp_file_path]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    for line in process.stdout:
        yield 'data: %s\n\n' % line.decode('utf-8')
