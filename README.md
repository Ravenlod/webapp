# webapp
Как подтянуть необходимые модули:
  pip install -r /requirements.txt
Как поднять веб-приложение:
export FLASK_ENV=development
export FLASK_APP=app
flask run -h 0.0.0.0:5000


Try insert these commands, if standard pip isn't working:

sudo apt install libcairo2-dev libxt-dev libgirepository1.0-dev
pip install pycairo PyGObject

Or:

sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
pip install pycairo
pip install PyGObject

Installing D-spy:

apt install flatpak
apt install gnome-software-plugin-flatpak
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

Restart the system

flatpak install flathub org.gnome.dspy

Run application:
flatpak run org.gnome.dspy

Check for D-bus daemon is working properly:

dbus-daemon --version


