# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'
from django.utils.translation import ugettext_lazy as _
from fabric.api import *

supervisor_reload_commands = ["supervisorctl reread","supervisorctl update"]

templates = {
    "nginx-basic": {
        "local_path": "etc/v2/apprl.nginx.include.conf",
        "remote_path": "/etc/nginx/sites-available/%(project_name)s.include.conf",
        #"reload_command": ["supervisorctl nginx restart"],
    },
    "nginx-basic-v2": {
        "local_path": "etc/v2/apprl.nginx.include2.conf",
        "remote_path": "/etc/nginx/sites-available/%(project_name)s.include.conf",
        #"reload_command": ["supervisorctl nginx restart"],
    },
    # Make sure theres a symlink
    "nginx-application": {
        "local_path": "etc/v2/%(settings)s/apprl.nginx.conf.%(settings)s",
        "remote_path": "/etc/nginx/sites-available/%(project_name)s.conf",
        "reload_command": ["supervisorctl restart nginx"],
    },
    "supervisor-nginx": {
        "local_path": "etc/v2/supervisor-nginx.conf",
        "remote_path": "/etc/supervisor/conf.d/nginx.conf",
        "reload_command": supervisor_reload_commands,
    },
    "supervisor-redis": {
        "local_path": "etc/v2/supervisor-redis.conf",
        "remote_path": "/etc/supervisor/conf.d/redis.conf",
        "reload_command": supervisor_reload_commands,
    },
    "supervisor-memcached": {
        "local_path": "etc/v2/supervisor-memcached.conf",
        "remote_path": "/etc/supervisor/conf.d/memcached.conf",
        "reload_command": supervisor_reload_commands,
    },
    #"cron": {
    #    "local_path": "etc/crontab",
    #    "remote_path": "/etc/cron.d/%(proj_name)s",
    #    "owner": "root",
    #    "mode": "600",
    #},
    "gunicorn": {
        "local_path": "etc/v2/gunicorn.conf.py",
        "remote_path": "%(project_path)s/gunicorn.conf.py",
        #"reload_command": ["supervisorctl restart gunicorn_%(project_name)s"],
    },
     "supervisor-gunicorn": {
        "local_path": "etc/v2/supervisor-gunicorn.conf",
        "remote_path": "/etc/supervisor/conf.d/gunicorn.conf",
        "reload_command": supervisor_reload_commands,
    },
    "supervisor-gunicorn-admin": {
        "local_path": "etc/v2/supervisor-gunicorn-admin.conf",
        "remote_path": "/etc/supervisor/conf.d/gunicorn-admin.conf",
        "reload_command": supervisor_reload_commands,
    },
    "gunicorn-admin": {
        "local_path": "etc/v2/gunicorn-admin.conf.py",
        "remote_path": "%(project_path)s/gunicorn-admin.conf.py",
        #"reload_command": ["supervisorctl restart gunicorn_%(project_name)s_admin"],
    },
    "supervisor-celery": {
        "local_path": "etc/v2/supervisor-celery.conf",
        "remote_path": "/etc/supervisor/conf.d/celery.conf",
        "reload_command": supervisor_reload_commands,
    },
}

def common_aws():
    env.settings = 'production-aws'
    env.forward_agent = True
    env.use_ssh_config = True
    env.user = 'deploy'
    env.group = env.user
    env.run_user = 'www-data'
    env.installed_apps = ['supervisor-gunicorn','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
                            # Mostly involves shared servers when for example memacached is already installed.
    env.venv_home = "/home/%(user)s" % env
    env.venv_path = "%(venv_home)s/%(project_name)s" % env
    env.path = env.venv_path
    env.home_path = '/home/%(user)s' % env
    env.project_dirname = 'project'
    env.project_path = "%(venv_path)s/%(project_dirname)s" % env
    env.celery_processes = '0'
    env.celery_processes_background = '0'
    env.gunicorn_admin_processes = '2'
    env.gunicorn_port = 8090
    env.gunicorn_admin_port = 8095
    env.locale = "en_US.UTF-8"
    env.repo_url = "git@github.com:martinlanden/apprl.git"
    env.manage = "%(venv_path)s/bin/python %(project_path)s/manage.py" % env
    env.reqs_path = 'etc/requirements.pip'
    env.git = env.repo_url.startswith("git") or env.repo_url.endswith(".git")

def common_local():
    env.settings = 'local_dev'
    env.forward_agent = True
    env.use_ssh_config = False
    env.user = 'deploy'
    env.group = env.user
    env.run_user = env.user
    env.installed_apps = ['supervisor-memcached','supervisor-redis'] # Empty means everything. Depends on what else is already on the server at the time.
                            # Mostly involves shared servers when for example memacached is already installed.
    env.venv_home = "/home/%(user)s" % env
    env.venv_path = "%(venv_home)s/%(project_name)s" % env
    env.path = env.venv_path
    env.home_path = '/home/%(user)s' % env
    env.project_dirname = 'project'
    env.project_path = "%(venv_path)s/%(project_dirname)s" % env
    env.celery_processes = '0'
    env.celery_processes_background = '0'
    env.memcached_url = 'localhost'
    env.locale = "en_US.UTF-8"
    env.repo_url = "git@github.com:martinlanden/apprl.git"
    env.manage = "%(venv_path)s/bin/python %(project_path)s/manage.py" % env
    env.reqs_path = 'etc/requirements.pip'
    env.git = env.repo_url.startswith("git") or env.repo_url.endswith(".git")