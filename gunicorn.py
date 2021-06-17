import os
import gevent.monkey
gevent.monkey.patch_all()
import multiprocessing

#bind = '0.0.0.0:8001'
reload = False
loglevel = 'info'
accesslog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s %(r)s %(s)s %(b)s %(D)s %(f)s %(a)s'
errorlog = '-'


workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gunicorn.workers.ggevent.GeventWorker'
