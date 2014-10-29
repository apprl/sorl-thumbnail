# -*- coding: utf-8 -*-
from fabric.colors import green

__author__ = 'klaswikblad'
import os
from django.utils.translation import ugettext_lazy as _
from fabric.api import *
from fabric.contrib.files import upload_template

if os.path.exists(os.path.join(os.path.dirname(__file__), "fab_utils.py")):
    from fab_utils import postgres, print_command
    green("Loading utils settings", bold=True)
else:
    red("Failed to load util settings", bold=True)

def setup_solr_server():
    """
    Setup a data server with both Apache Solr and PostgreSQL.
    """
    require('hosts', provided_by=[dev_op])
    require('path')
    require('solr_path')

    sudo('apt-get update -q')
    sudo('apt-get install -q -y openjdk-7-jre-headless')
    run('mkdir -p {solr_path}'.format(**env))

def psql(sql, show=True):
    """
    Runs SQL against the project's database.
    """
    out = postgres('psql -c "%s"' % sql)
    if show:
        print_command(sql)
    return out

@task
def install_nginx():
    # install nginx, remember to add daemon off to settings.
    sudo('apt-get install -y nginx')
    # disable default site
    #sudo('mkdir -p /var/log/nginx')
    sudo('mkdir -p /var/log/nginx/client_body_temp /var/log/nginx/proxy_temp;' % env)
    with settings(warn_only=True):
        sudo('cd /etc/nginx/conf-enabled/; rm -f default;' % env, pty=True)
        sudo('cd /etc/nginx/sites-enabled/; rm -f default;' % env, pty=True)
    #sudo('service nginx stop;mv /etc/init.d/nginx /etc/nginx.bak')
    upload_template('etc/v2/supervisor-nginx.conf','/etc/supervisor/conf.d/nginx.conf', use_sudo=True)
    upload_template('etc/v2/nginx.conf','/etc/nginx.conf', use_sudo=True)
    sudo('cd /etc/nginx/sites-enabled/;ln -s ../sites-available/%(project_name)s.conf %(project_name)s.conf' % env)
    sudo('supervisorctl reread')
    sudo('supervisorctl add nginx')
    #sudo('supervisorctl start nginx')

@task
def install_supervisor():
    sudo('apt-get install supervisor')
    # Installing wildcards globally since the supervisor service runs as root globally
    sudo('pip install supervisor-wildcards')
    upload_template('etc/v2/supervisor.conf','/etc/supervisor/supervisor.conf',context=env, use_sudo=True)
    sudo('service supervisor restart')

@task
def install_memcached():
    # install memcached
    sudo('apt-get install -y -q memcached')
    # Add template files for control through supervisorctl
    sudo('mkdir -p /var/log/memcached; chown %(user)s:%(group)s /var/log/memcached;' % env, pty=True)
    upload_template('etc/v2/supervisor-memcached.conf','/etc/supervisor/conf.d/memcached.conf',context=env, use_sudo=True)
    sudo('service memcached stop;mv /etc/init.d/memcached /etc/memcached.bak')
    sudo('supervisorctl reread')
    sudo('supervisorctl add memcached')

@task
def install_redis():
    sudo('apt-get install -y redis-server')
    sudo('mkdir -p /var/redis /var/lib/redis /var/log/redis', pty=True)
    sudo('touch /var/log/redis/stdout.log;touch /var/log/redis/stderr.log;touch /var/log/redis/stdout.log')
    sudo('chown redis /var/redis;chown -R redis /var/log/redis;', pty=True)
    sudo('service redis-server stop')
    sudo('mv /etc/init.d/redis-server /etc/redis-server.bak')
    upload_template('etc/v2/redis.conf','/etc/redis.conf', use_sudo=True)
    upload_template('etc/v2/supervisor-redis.conf','/etc/supervisor/conf.d/redis.conf',context=env, use_sudo=True)
    sudo('supervisorctl reread')
    sudo('supervisorctl add redis')

@task
def install_gunicorn():
    upload_template('etc/v2/supervisor-gunicorn.conf','/etc/supervisor/conf.d/gunicorn.conf',context=env, use_sudo=True)
    sudo('mkdir -p /var/log/gunicorn', pty=True)
    sudo('chown %(run_user)s:%(user)s /var/log/gunicorn' % env, pty=True)
    #sudo('supervisorctl reread')
    #sudo('supervisorctl add gunicorn_%(project_name)s' % env)

@task
def install_gunicorn_admin():
    upload_template('etc/v2/supervisor-gunicorn-admin.conf','/etc/supervisor/conf.d/gunicorn-admin.conf',context=env, use_sudo=True)
    sudo('mkdir -p /var/log/gunicorn', pty=True)
    sudo('chown %(run_user)s:%(user)s /var/log/gunicorn' % env, pty=True)
    #sudo('supervisorctl reread')
    #sudo('supervisorctl add gunicorn_%(project_name)s_admin' % env)

@task
def install_celery():
    upload_template('etc/v2/supervisor-celery.conf','/etc/supervisor/conf.d/celery.conf' % env,context=env, use_sudo=True)
    upload_template('etc/v2/supervisor-celery-background.conf','/etc/supervisor/conf.d/celery-background.conf' % env,context=env, use_sudo=True)
    upload_template('etc/v2/supervisor-celery-beat.conf','/etc/supervisor/conf.d/celery-beat.conf' % env,context=env, use_sudo=True)
    sudo('mkdir /var/run/celery;chown %(run_user)s /var/run/celery' % env)
    #sudo('mkdir -p %(venv_path)s/var/run;chown -R %(run_user)s:%(user)s %(venv_path)s/var' % env, pty=True)
    sudo('mkdir -p /var/log/celery', pty=True)
    sudo('chown %(run_user)s:%(user)s /var/log/celery' % env, pty=True)
    sudo('supervisorctl reread')
    sudo('supervisorctl add celery_%(project_name)s_beat' % env)
    sudo('supervisorctl add celery_workers' % env)
