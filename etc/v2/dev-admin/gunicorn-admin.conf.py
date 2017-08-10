from __future__ import unicode_literals
import multiprocessing

bind = "127.0.0.1:%(gunicorn_admin_port)s"
workers = "%(gunicorn_admin_processes)s"
loglevel = "error"
proc_name = "%(project_name)s-admin"
