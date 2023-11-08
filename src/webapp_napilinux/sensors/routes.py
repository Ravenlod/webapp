import glob
import shutil
from os import path, remove, mkdir

from flask_login import login_required
from werkzeug.security import safe_join
from werkzeug.utils import secure_filename

from webapp_napilinux.forms.sensors import SensorsTextConf, SensorAddConf

from flask import render_template, current_app, flash, request, redirect, url_for, send_file

from webapp_napilinux.utils import allowed_file, sys_service_manage


def routes(bp):
    @bp.route("/", methods=['GET'])
    @login_required
    def index():
        def read_comment():
            comment = str()
            with open(upload_path, "r") as file:
                lines = file.readlines()
                for line in lines:
                    if line.startswith('##'):
                        comment = line.split('##', 1)[1]
                file.close()
            return comment

        sensors_list = list()
        for f in reversed(sorted(glob.glob(current_app.config["UPLOAD_FOLDER"] + "*.conf"), key=path.getmtime)):
            name = str(f).split("/")[-1].split(".")[0]
            active_path = safe_join(current_app.config["ACTIVE_FOLDER"], f"{name}.conf")
            upload_path = safe_join(current_app.config["UPLOAD_FOLDER"], f"{name}.conf")
            active = path.exists(active_path)
            comment_line = read_comment()
            sensors_list.append((name, comment_line, active,))
        return render_template('sensors/index.html', sensors_list=sensors_list)


    @bp.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload_sensor():
        if request.method == 'POST':

            if 'file' not in request.files:
                flash('No file part')
                return redirect(request.url)
            file = request.files['file']
            # TODO: Check file size and output alert
            # weight = 50
            # if file.seek(0,2) > weight:
            #     print('LARGE')
            #     flash(f'Слишком большой файл! Больше чем разрешено на {file.seek(0,2)-weight}Bytes')
            #     flash(file.tell())
            #     return redirect(request.url)
            if file.filename == '':
                flash('Не выбран файл!')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(path.join(current_app.config['UPLOAD_FOLDER'], filename))
                return redirect(url_for('sensors.index', name=filename))
            else:
                flash('Файл имеет неверный формат!')

        return render_template('sensors/upload.html'), 201


    @bp.route("/<sensor_name>", methods=['GET', 'POST'])
    @login_required
    def sensor(sensor_name):
        # form = SensorsSettingsForm(request.form)
        filename = f'{sensor_name}.conf'
        active_path = safe_join(current_app.config["ACTIVE_FOLDER"], filename)
        upload_path = safe_join(current_app.config["UPLOAD_FOLDER"], filename)
        active_folder_path = safe_join(current_app.config["ACTIVE_FOLDER"])

        # View *.conf URL param
        view_conf = request.args.get('view')

        if request.method == 'GET' and view_conf == 'y':
            with open(upload_path, "r") as f:
                text = f.read()
                f.close()
            return render_template('sensors/viewconf.html', text=text)

        # Download *.conf URL param
        download_conf = request.args.get('download')

        if request.method == 'GET' and download_conf == 'y':
            return send_file(upload_path, as_attachment=True)

        # Delete *.conf URL param
        delete_conf = request.args.get('delete')

        if request.method == 'GET' and delete_conf == 'y':
            if path.exists(active_path) is True:
                flash('Шаблон активен, удалить невозможно!')
            else:
                try:
                    remove(upload_path)
                except FileNotFoundError:
                    return 'Ошибка удаления файла, файл конфигурации не найден', 404
            return redirect(request.referrer)

        # Enabled  *.conf URL param
        enable_conf = request.args.get('enable')

        if request.method == 'GET' and enable_conf == 'y':
            if path.exists(upload_path) is True:
                # Create dir if not exist
                if path.exists(active_folder_path) is False:
                    mkdir(active_folder_path)
                if path.exists(active_path) is False:
                    shutil.copyfile(upload_path, active_path)
                    sys_service_manage('telegraf')
                else:
                    flash("Шаблон уже активен!")
                return redirect(url_for('sensors.index', name=filename))

        # Disabled *.conf URL param
        disable_conf = request.args.get('disable')

        if request.method == 'GET' and disable_conf == 'y':
            if path.exists(active_path):
                remove(active_path)
                sys_service_manage('telegraf')
            else:
                flash('Шаблон по какой-то причине отсутствует в списке активных')
            return redirect(url_for('sensors.index', name=filename))

        # Upgrade *.conf URL param
        form_conf = SensorsTextConf()

        upg_conf = request.args.get('upg')

        if request.method == 'POST' and upg_conf == 'y':
            conf_text = request.form.get(form_conf.conf_text_area.name)
            with open(active_path, 'w') as f_new:
                f_new.write(str(conf_text))
                f_new.close()
            sys_service_manage('telegraf')
            return redirect(request.referrer)

        def readfile():
            with open(active_path, "r") as fa:
                read_file = fa.read()
                # text = text.replace('\n', '<br>')
                # return Response(text, mimetype='application/toml')
                fa.close()
                return read_file

        if path.exists(active_path) is True:
            text = readfile()
        else:
            flash("Сперва нужно активировать шаблон.")

            return redirect(url_for('sensors.index', name=filename))
        return render_template('sensors/sensor.html', text=text, form_conf=form_conf, current_sensor=request.path)


    @bp.route('/add', methods=['GET', 'POST'])
    @login_required
    def add_sensor():
        form = SensorAddConf()
        if request.method == 'POST':
            file = f'{request.form.get(form.sensor_name.name)}.conf'
            file_name = secure_filename(file)
            upload_path = safe_join(current_app.config["UPLOAD_FOLDER"], file_name)
            conf_text = request.form.get(form.conf_text.name)
            with open(upload_path, 'w') as f_new:
                f_new.write(str(conf_text))
                f_new.close()
            return redirect(url_for('sensors.index'))

        return render_template('sensors/add.html', form=form)
