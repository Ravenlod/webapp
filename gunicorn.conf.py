workers = 1
worker_class = "gevent"
wsgi_app = "app:create_app()"
bind = "0.0.0.0:8081"
# chdir = "/var/www/web"
# errorlog = "/home/root/error.log"
# accesslog = "/home/root/access.log"
