import subprocess
import time
from os import popen, path, system
# from datetime import datetime
from pydbus import SystemBus
from flask import flash
from gi.repository import GLib

ALLOWED_EXTENSIONS = {'conf'}


class ModemControl:
    current_bearer = str()
    current_name = str()
    current_bearer_path = str()

    def modem_check_state(self):
        try:
            obj_current_modem = self.modem_current()
            modem_state = obj_current_modem['org.freedesktop.DBus.Properties'].Get(
                'org.freedesktop.ModemManager1.Modem', 'State')
            return modem_state
        except Exception:
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

    @staticmethod
    def modem_add_connection(config_input: tuple[str, int, str, str]):
        config_path = "/etc/modem/modem.conf"
        service_name = "modem-connection-control"
        config_vars = "IS_MODEM_CONNECTED", "apn", "ip-type", "user", "password"
        try:

            final_config_input = list(config_input)
            final_config_input.insert(0, "true")
            sys_change_config_file(config_path, config_vars, final_config_input)

            sys_service_manage(service_name, "start")

        except Exception as err:
            print(err)
            return err.args
        except KeyError:
            print("Critical error")
            return 'Critical error'

    @staticmethod
    def modem_delete_connection():
        config_path = "/etc/modem/modem.conf"
        service_name = "modem-connection-control"
        config_var = "IS_MODEM_CONNECTED"
        line_list = list()
        
        try:
            sys_change_config_file(config_path, (config_var,), ["false"])
    
            sys_service_manage(service_name, "start")
        except Exception as err:
            print(err)
            return err.args
        except KeyError:
            print("Critical error")
            return 'Critical error'

    def modem_add_connection_mm(self, config_input: tuple[str, int, str, str]):
        # apn, ip-type, user, password
        """Пытается подключить модем, в случае успеха возвращает путь на текущий носитель,
        или код ошибки при обработки исключения"""
        try:
            bus = SystemBus()
            obj_current_modem = self.modem_current()
            obj_current_modem['org.freedesktop.ModemManager1.Modem'].Enable(True)

            time.sleep(15)
            # TODO timer
            ports = obj_current_modem['org.freedesktop.DBus.Properties'].Get('org.freedesktop.ModemManager1.Modem',
                                                                             'Ports')
            simple_connect = obj_current_modem['org.freedesktop.ModemManager1.Modem.Simple']
            bearer_path = simple_connect.Connect({'apn': GLib.Variant.new_string(config_input[0]),
                                                  'ip-type': GLib.Variant.new_int32(int(config_input[1])),
                                                  'user': GLib.Variant.new_string(config_input[2]),
                                                  'password': GLib.Variant.new_string(config_input[3])})
            self.current_bearer_path = bearer_path

            self.current_bearer = bus.get("org.freedesktop.ModemManager1", bearer_path)
            ip_dict: dict = self.current_bearer['org.freedesktop.DBus.Properties'].Get(
                'org.freedesktop.ModemManager1.Bearer', 'Ip4Config')
            self.current_name: str = [port[0] for port in ports if "ww" in port[0]][0]

            config_input = (self.current_name, ip_dict['address'], ip_dict['gateway'],
                            (ip_dict['dns1'], ip_dict['dns2']))
            # TODO Потенциальная ошибка, если DNS будет один экземпляр
            sys_wireless_network_config(config_input)
            sys_service_manage('systemd-networkd')
            sys_manage_ip_route(self.current_name, 500)
            return bearer_path

        except Exception as err:
            return err.args
        except KeyError:
            return 'Critical error'

    def modem_delete_connection_mm(self):
        try:
            obj_current_modem = self.modem_current()
            ports = obj_current_modem['org.freedesktop.DBus.Properties'].Get(
                'org.freedesktop.ModemManager1.Modem', 'Ports')
            self.current_name = [port[0] for port in ports if "ww" in port[0]][0]
            sys_manage_ip_route(self.current_name, 500, "delete")
            simple_connect = obj_current_modem['org.freedesktop.ModemManager1.Modem.Simple']

            simple_connect.Disconnect('/')

            time.sleep(5)
            # if self.modem_check_state() == 8:
            obj_current_modem['org.freedesktop.ModemManager1.Modem'].Enable(False)

            # else:
            #     raise Exception(self.modem_check_state())
            sys_wireless_config_clear()
            sys_service_manage('systemd-networkd')

            return True
        except Exception as err:
            print(type(err))
            return err

    @staticmethod
    def modem_get_current_bearer_properties(property_name: str, bearer_path: str):
        bus = SystemBus()

        try:
            current_bearer = bus.get("org.freedesktop.ModemManager1", bearer_path)
            property_value = current_bearer['org.freedesktop.DBus.Properties'].Get(
                'org.freedesktop.ModemManager1.Bearer', property_name)

            return property_value
        except Exception as e:

            return e

    @staticmethod
    def modem_current():
        bus = SystemBus()
        try:
            # Root object
            obj_root = bus.get('.ModemManager1', '/org/freedesktop/ModemManager1')
            # Modem
            obj_current_modem = bus.get('.ModemManager1',
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
        """Метод, возвращающий код состояния сессии USSD.
MM_MODEM_3GPP_USSD_SESSION_STATE_UNKNOWN = 0 - Unknown state;
MM_MODEM_3GPP_USSD_SESSION_STATE_IDLE = 1 - No active session;
MM_MODEM_3GPP_USSD_SESSION_STATE_ACTIVE = 2 - A session is active and the mobile is waiting for a response;
MM_MODEM_3GPP_USSD_SESSION_STATE_USER_RESPONSE = 3 - The network is waiting for the client's response."""
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

    def modem_get_init_apn(self):
        """ Метод, который позволяет настроить APN для текущего профиля"""
        try:
            obj_current_modem = self.modem_current()
            apn_set = obj_current_modem['org.freedesktop.ModemManager1.Modem.Modem3gpp.ProfileManager']
            # apn_set.Set({'profile-id': GLib.Variant.new_int32(1), 'apn': GLib.Variant.new_string(str(apn_input))})
            response = apn_set.List()[0]['apn']
            return response
        except GLib.GError as err:
            # print(err.args)
            return 'internet'

    def modem_info(self):
        # DBUS lib tutorial https://github.com/LEW21/pydbus/blob/master/doc/tutorial.rst
        try:
            obj_current_modem = self.modem_current()
            current_modem = obj_current_modem['org.freedesktop.ModemManager1.Modem']

            # Values
            info = dict()
            # print(current_modem.Sim)
            # print(current_modem.SimSlots)

            if any(slot != '/' for slot in current_modem.Sim):
                # TODO Проблема с односимочными модемами
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
                # print(line)
                if line.startswith(word):
                    if line.find(word) != -1:
                        result = line.split('=', 1)[1]
            f.close()
            # print("Result: ", result)
        return result

    def ip_current(self):
        net = popen(
            f'networkctl status | head -n8'
        ).read()
        return net


def findparam(_path, word):
    with open(_path, "r") as f:
        text = f.readlines()
        for line in text:
            if line.startswith(word):
                if line.find(word) != -1:
                    result = line.split('=', 1)[1]
        f.close()
    return result


def sys_wireless_network_config(config_input: tuple[str, str, str, tuple[str]]):
    """Считывает данные с входного кортежа, и записывает в конфигурационый файл для сервиса systemd-networkd"""
    config_path = '/etc/systemd/network/30-modem.network'
    with open(config_path, 'w') as f:
        # TODO Доделать обработчик ошибок
        row = ','.join(config_input[3])
        line1 = '[Match]\n'
        line2 = '\n'
        line3 = f'Name={config_input[0]}\n'
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


def sys_wireless_config_clear():
    config_path = '/etc/systemd/network/30-modem.network'
    cmd = f'truncate -s 0 {config_path}'
    try:
        subprocess.check_output(cmd, universal_newlines=True, shell=True)

    except subprocess.CalledProcessError:
        flash("Недостаточно системных прав!")
        pass


def sys_execute_external_script(config_path: str):
    try:
        subprocess.check_output(config_path, universal_newlines=True, shell=True)
    except Exception as err:
        print(err)
        pass
    except KeyError as kerr:
        print(kerr)


def sys_change_config_file(file_path: str, name_prop_list: tuple, input_list: list):
    line_list = list()
    with open(file_path, "r") as config:
        i = 0
        line_list = config.readlines()
        for index, line in enumerate(line_list):
            if name_prop_list[i] in line:
                # print(line, i)
                line_list[index] = str(name_prop_list[i]) + '=' + str(input_list[i]) + '\n'
                if i == len(name_prop_list) - 1:
                    break
                i += 1
    with open(file_path, "w") as config:
        # print(line_list)
        config.writelines(line_list)


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


def sys_soft_reset():
    system('fw_setenv -f /etc/u-boot-default-env resetroot yes')


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
    sys_service_manage("influxdb")


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
        flash("Недостаточно системных прав!")
        pass


def sys_service_manage(service, command="restart"):
    line = []
    match command:
        case "restart":
            line = [f"sudo systemctl restart {service}.service"]
        case "start":
            line = [f"sudo systemctl start {service}.service"]
        case "stop":
            line = [f"sudo systemctl stop {service}.service"]
        case _:
            pass

    # stop = [f"sudo systemctl stop {service}.service"]
    # start = [f"sudo systemctl start {service}.service"]
    try:
        subprocess.check_output(line, universal_newlines=True, shell=True)
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
