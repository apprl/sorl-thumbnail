# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

import os
from fabric.colors import green, red
from fabric.api import *

if os.path.exists(os.path.join(os.path.dirname(__file__), "fab_apps.py")):
    from fab_apps import *
    green("Loading app settings", bold=True)
else:
    red("Failed to load app settings", bold=True)

def prod_settings():
    env.db_name = 'apparel'
    env.db_user = 'apparel'
    env.db_pass = 'gUp8Swub'
    env.db_url = 'appareldbinstance.cnzaoxvvyal7.eu-west-1.rds.amazonaws.com'
    env.memcached_url = 'apparel-cache.uhyk4j.cfg.euw1.cache.amazonaws.com'
    env.redis_url = "ip-10-0-1-166.eu-west-1.compute.internal"
    env.solr_url =  "ip-10-0-1-38.eu-west-1.compute.internal"
    env.s3_url = "s.apprl.com"
    env.gateway = 'deploy@bastion'


def localhost():
    "Use the local virtual server"
    env.hosts = ['localhost']
    env.user = 'klaswikblad'
    env.group = env.user
    env.path = '/Users/%(user)s/PycharmProjects/apparelenv/apparelrow/' % env
    env.solr_path = '/Users/%(user)s/PycharmProjects/apparelenv/apparelrow/solr-apprl/' % env

def dev_op():
    "Use the local virtual server"
    #if not vm_bridge:
    #    env.hosts = ['192.168.1.38']
    #else:
    env.hosts = ['apprlvm']
    env.settings = 'apprlvm'
    env.user = 'deploy'
    env.group = env.user
    env.path = '/home/%(user)s/%(project_name)s/' % env
    env.path = '/home/{user}/{project_name}'.format(**env)
    env.solr_path = '/Users/%(user)s/PycharmProjects/apparelenv/apparelrow/solr-apprl/' % env
    env.solr_path = '/home/{user}/solr'.format(**env)

def dev_production_v2():
    #if not vm_bridge:
    #    env.hosts = ['192.168.1.38']
    #else:
    env.hosts = ['apprlvm2']

    env.settings = 'localprod'
    env.user = 'deploy'
    env.group = env.user
    env.run_user = 'www-data'
    env.installed_apps = ['gunicorn','gunicorn-admin'] # Empty means everything. Depends on what else is already on the server at the time.
                            # Mostly involves shared servers when for example memacached is already installed.
    env.installed_apps = []
    env.hostname="staging1"
    env.venv_home = "/home/%(user)s" % env
    env.venv_path = "%(venv_home)s/%(project_name)s" % env
    env.path = env.venv_path
    env.home_path = '/home/%(user)s' % env
    env.project_dirname = 'project'
    env.project_path = "%(venv_path)s/%(project_dirname)s" % env
    env.celery_processes = '1'
    env.celery_processes_background = '1'
    env.memcached_url = '127.0.0.1'
    env.gunicorn_processes = '1'
    env.gunicorn_admin_processes = '1'
    env.gunicorn_port = 8090
    env.gunicorn_admin_port = 8095
    env.locale = "en_GB.UTF-8"
    env.repo_url = "git@github.com:martinlanden/apprl.git"
    env.db_pass = 'apprl'
    env.db_name = 'apprl'
    env.db_user = 'apparel'
    env.db_url = 'apprlvm'
    env.manage = "%(venv_path)s/bin/python %(project_path)s/manage.py" % env
    env.reqs_path = 'etc/requirements.pip'
    env.git = env.repo_url.startswith("git") or env.repo_url.endswith(".git")


def production_web_v2():
    env.hosts = ['web-v2.apprl.com']
    env.settings = 'production-v2'
    env.user = 'deploy'
    env.group = env.user
    env.run_user = 'www-data'
    env.installed_apps = ['gunicorn','gunicorn-admin'] # Empty means everything. Depends on what else is already on the server at the time.
                            # Mostly involves shared servers when for example memacached is already installed.
    env.hostname="web-v2"
    env.venv_home = "/home/%(user)s" % env
    env.venv_path = "%(venv_home)s/%(project_name)s" % env
    env.path = env.venv_path
    env.home_path = '/home/%(user)s' % env
    env.project_dirname = 'project'
    env.project_path = "%(venv_path)s/%(project_dirname)s" % env
    env.celery_processes = '3'
    env.celery_processes_background = '2'
    env.memcached_url = '127.0.0.1'
    env.gunicorn_admin_processes = '1'
    env.gunicorn_port = 8090
    env.gunicorn_admin_port = 8095
    env.locale = "en_GB.UTF-8"
    env.repo_url = "git@github.com:martinlanden/apprl.git"
    env.db_name = 'apparel'
    env.db_user = 'apparel'
    env.db_pass = 'ashwe3'
    env.db_url = '146.185.137.189'
    env.manage = "%(venv_path)s/bin/python %(project_path)s/manage.py" % env
    env.reqs_path = 'etc/requirements.pip'
    env.git = env.repo_url.startswith("git") or env.repo_url.endswith(".git")


@task
def production_web_aws_2():
    common_aws()
    prod_settings()
    env.internal_ip = '10.0.0.211'
    env.hosts = ['%(user)s@%(internal_ip)s' % env]
    env.installed_apps = ['supervisor-gunicorn','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
    env.restart = ['gunicorn','nginx']
    env.hostname="web-aws2"

@task
def production_web_aws_3():
    common_aws()
    prod_settings()
    env.internal_ip = '10.0.0.18'
    env.hosts = ['%(user)s@%(internal_ip)s' % env]
    env.installed_apps = ['supervisor-gunicorn','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
    env.restart = ['gunicorn','nginx']
    env.hostname="web-aws3"

@task
def production_web_aws_4():
    common_aws()
    prod_settings()
    env.internal_ip = '10.0.0.168'
    env.hosts = ['%(user)s@%(internal_ip)s' % env]
    env.installed_apps = ['supervisor-gunicorn','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
    env.restart = ['gunicorn','nginx']
    env.hostname="web-aws4"

@task
def production_aws_admin():
    common_aws()
    prod_settings()
    env.settings = 'production-admin'
    env.internal_ip = '10.0.0.89'
    env.hosts = ['%(user)s@%(internal_ip)s' % env]
    env.installed_apps = ['supervisor-gunicorn-admin','gunicorn-admin','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
    env.restart = ['gunicorn_admin','nginx']
    env.hostname = 'admin'

