# webapp

Сборка пакетных файлов для webapp:

```shell
python -m build
```

How to pull up all dependencies:

```shell
pip install -r /requirements.txt
```

How to run flask application:

```shell
export FLASK_DEBUG=true
export FLASK_APP=app
flask run -h 0.0.0.0 -p 5000
```

How to kill flask process:

```shell
sudo kill -9 $(pgrep flask)
```

Try insert these commands, if standard pip isn't working:

```shell
sudo apt install libcairo2-dev libxt-dev libgirepository1.0-dev
pip install pycairo PyGObject
```

Or:

```shell
sudo apt install libgirepository1.0-dev libcairo2-dev
sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
pip install pycairo
pip install PyGObject
```

Or:

```shell
sudo pacman -S libgirepository
sudo pacman -S gobject-introspection
```

Installing D-spy:

```shell
apt install flatpak
apt install gnome-software-plugin-flatpak
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

Restart the system

```shell
flatpak update
flatpak install flathub org.gnome.dspy
```

Run application:

```shell
flatpak run org.gnome.dspy
```

Check for D-bus daemon is working properly:

```shell
dbus-daemon --version
```
