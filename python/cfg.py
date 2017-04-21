loglevel = 'debug'
daemon = False
bind = '0.0.0.0:8000'
timeout = 5
graceful_timeout = 60 
worker_class = 'sync'
workers = 1
from kontrol.endpoint import up, down
def post_worker_init(worker):
    up()
def worker_int(worker):
    down()
