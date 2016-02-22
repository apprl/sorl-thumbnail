# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

from fabric.colors import green, red
import os
from fabric.api import *


if os.path.exists(os.path.join(os.path.dirname(__file__), "fab_apps.py")):
    from fab_apps import *
    green("Loading app settings", bold=True)
else:
    red("Failed to load app settings", bold=True)

def dev_settings():
    env.db_name = 'apparel'
    env.db_user = 'apparel'
    env.db_pass = '0p1a7IUmE6NU'
    env.db_url = 'apprldbinstance.cirbmil58ncc.us-east-1.rds.amazonaws.com'
    env.memcached_url = "apprl-cache-cluster.naojmu.cfg.use1.cache.amazonaws.com"
    env.redis_url = "ip-10-0-1-249.ec2.internal"
    env.solr_url = "ip-10-0-1-247.ec2.internal"
    env.s3_url = "s-staging.apprl.com"
    env.gateway = 'deploy@dev-bastion'
    env.aws_key_id = 'AKIAJ2AF5IHPHTQH4QUA'
    env.aws_key = '0xyH+ANAXckDhEHxOntnlLKAh/ONC4g6KB3hpHKX'
    env.sentry_url = ''


def localhost():
    "Use the local virtual server"
    env.hosts = ['localhost']
    env.user = 'klaswikblad'
    env.group = env.user
    env.path = '/Users/%(user)s/PycharmProjects/apparelenv/apparelrow/' % env
    env.solr_path = '/Users/%(user)s/PycharmProjects/apparelenv/apparelrow/solr-apprl/' % env

@task
def dev_local():
    "Use the local virtual server"
    env.hosts = ['192.168.1.71']
    common_local()
    env.user = 'deploy'
    env.group = env.user
    env.db_name = 'apparel'
    env.db_user = 'apparel'
    env.db_pass = 'apparel'
    env.db_url = 'localhost'
    env.memcached_url = 'localhost'
    env.redis_url = 'localhost'
    env.solr_url = 'localhost'
    env.s3_url = "none"

    env.path = '/Users/%(user)s/jasper/apparelenv/apparelrow/' % env
    env.solr_path = '/Users/%(user)s/jasper/apparelenv/apparelrow/solr-apprl/' % env


@task
def dev_aws_1():
    common_aws()
    dev_settings()
    env.settings = "dev-aws"
    env.internal_ip = "10.0.0.213"
    env.hosts = ['%(user)s@%(internal_ip)s' % env]
    env.installed_apps = ['supervisor-gunicorn','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
    env.restart = ['gunicorn','nginx']
    env.hostname="dev-aws1"
    env.sentry_url = "https://860283083f7f4a9a8c36e6a6c41a93a9:8366888ded5e46b495d114e5b0f64803@sentry.apprl.com/3"
    env.collectstatic = True

@task
def dev_aws_2():
    common_aws()
    dev_settings()
    env.settings = 'dev-aws'
    env.internal_ip = '10.0.0.214'
    env.hosts = ['%(user)s@%(internal_ip)s' % env]
    env.installed_apps = ['supervisor-gunicorn','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
    env.restart = ['gunicorn','nginx']
    env.hostname="dev-aws2"
    env.sentry_url = "https://860283083f7f4a9a8c36e6a6c41a93a9:8366888ded5e46b495d114e5b0f64803@sentry.apprl.com/3"
    env.collectstatic = True

@task
def dev_admin():
    common_aws()
    dev_settings()
    env.settings = "dev-admin"
    env.internal_ip = "10.0.0.54"
    env.hosts = ['%(user)s@%(internal_ip)s' % env]
    env.installed_apps = ['supervisor-gunicorn-admin','gunicorn-admin','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
                            # Mostly involves shared servers when for example memacached is already installed.
    env.restart = ['gunicorn_admin','nginx']
    env.hostname="dev-admin"
    env.sentry_url = "https://860283083f7f4a9a8c36e6a6c41a93a9:8366888ded5e46b495d114e5b0f64803@sentry.apprl.com/3"
    env.collectstatic = True

@task
def dev_solr():
    common_aws()
    dev_settings()
    env.settings = "dev-admin"
    env.hosts = ['%(user)s@ip-10-0-1-247.ec2.internal' % env]
    env.installed_apps = ['']
    env.hostname="solr"

@task
def dev_scrapy():
    common_aws()
    dev_settings()
    env.settings = "dev-scrapy-aws"
    env.hosts = ['%(user)s@ip-10-0-1-248.ec2.internal' % env]
    env.celery_processes = '1'
    env.celery_processes_background = '1'
    env.installed_apps = ['']
    env.run_user = env.user
    env.restart = ['scrapyd']
    env.reload_scrapy = True
    env.hostname="scrapy"


@task
def dev_importer():
    common_aws()
    dev_settings()
    env.settings = "dev-importer-aws"
    env.hosts = ['%(user)s@ip-10-0-1-249.ec2.internal' % env]
    env.celery_processes = '0'
    env.celery_processes_background = '0'
    env.installed_apps = ['']
    env.restart = []
    env.hostname="importer"

def prestaging_common(settings=None):
    env.settings = settings
    env.forward_agent = True
    env.use_ssh_config = True
    env.user = 'deploy'
    env.group = env.user
    env.run_user = 'www-data'
    #env.installed_apps = ['supervisor-gunicorn-norelic','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',]
    #env.installed_apps = ['supervisor-gunicorn-norelic','gunicorn',]
    env.installed_apps = ['']
    env.venv_home = "/home/%(user)s" % env
    env.venv_path = "%(venv_home)s/%(project_name)s-%(settings)s" % env
    env.path = env.venv_path
    env.home_path = '/home/%(user)s' % env
    env.project_name = "%s-%s" % (env.project_name,env.settings)
    env.project_dirname = 'project'
    env.project_path = "%(venv_path)s/%(project_dirname)s" % env
    env.celery_processes = '0'
    env.celery_processes_background = '0'
    env.gunicorn_admin_processes = '0'
    env.gunicorn_processes = '1'
    env.gunicorn_port = 8090
    #env.gunicorn_admin_port = 8095
    env.locale = "en_US.UTF-8"
    env.repo_url = "git@github.com:martinlanden/apprl.git"
    env.manage = "%(venv_path)s/bin/python %(project_path)s/manage.py" % env
    env.reqs_path = 'etc/requirements.pip'
    env.git = env.repo_url.startswith("git") or env.repo_url.endswith(".git")
    env.memcached_url = "sentry.apprl.com"
    env.redis_url = "sentry.apprl.com"
    env.solr_url = "localhost"
    env.s3_url = "s-prestage.apprl.com"
    #env.gateway = 'no gateway'
    #env.aws_key_id = 'AKIAJ2AF5IHPHTQH4QUA'
    #env.aws_key = '0xyH+ANAXckDhEHxOntnlLKAh/ONC4g6KB3hpHKX'
    env.aws_key_id = 'AKIAJWFWCTRXKCOCRPTQ'
    env.aws_key = 'rCUAw8IwyysB3u3pgDi5nKLsqJyGe2pchBc1on1a'
    env.sentry_url = 'https://fe5edd11a20c49d3bfe2d67933d7a515:affbc917003d4805b75141508941963d@sentry.apprl.com/5'
    env.restart = ['gunicorn_%(settings)s' % env]
    env.reload_scrapy = False
    env.db_user = 'apparel'
    env.db_pass = 'mAY06EfQJA'
    env.db_url = 'sentry.apprl.com'
    env.collectstatic = True

@task
def prestaging_1():
    env.settings = 'prestaging-1'
    env.hostname="prestaging-1"
    prestaging_common(env.settings)
    env.gunicorn_port = 8090
    env.hosts = ['%(settings)s.apprl.com' % env]
    env.db_name = 'apparel_%s' % env.settings.replace("-","_")
    env.branch = "feat-create_shop"
    env.collectstatic = False

@task
def prestaging_2():
    env.settings = 'prestaging-2'
    env.hostname="prestaging-2"
    prestaging_common(env.settings)
    env.gunicorn_port = 8091
    env.hosts = ['%(settings)s.apprl.com' % env]
    env.db_name = 'apparel_%s' % env.settings.replace("-","_")
    env.branch = "feat-product_widget"
    env.collectstatic = True
    env.restart = ['gunicorn']