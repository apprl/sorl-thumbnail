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
    env.memcached_path = "apprl-cache-cluster.naojmu.cfg.use1.cache.amazonaws.com"
    env.redis_url = "ip-10-0-1-249.ec2.internal"
    env.solr_url = "ip-10-0-1-247.ec2.internal"
    env.s3_url = "s-staging.apprl.com"
    env.gateway = 'deploy@dev-bastion'

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
    env.memcached_path = 'localhost'
    env.redis_url = 'localhost'
    env.solr_url = 'localhost'
    env.s3_url = "none"

    env.path = '/Users/%(user)s/PycharmProjects/apparelenv/apparelrow/' % env
    env.solr_path = '/Users/%(user)s/PycharmProjects/apparelenv/apparelrow/solr-apprl/' % env


@task
def dev_aws_1():
    common_aws()
    dev_settings()
    env.settings = 'dev-aws'
    env.hosts = ['%(user)s@ip-10-0-0-213.ec2.internal' % env]
    env.installed_apps = ['supervisor-gunicorn','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
    env.restart = ['gunicorn','nginx']
    ## local urls ##
    env.hostname="dev-aws1"
    env.internal_ip = "10.0.0.213"

@task
def dev_aws_2():
    common_aws()
    dev_settings()
    env.gateway = 'deploy@dev-bastion'
    env.settings = 'dev-aws'
    env.hosts = ['%(user)s@ec2-54-165-249-190.compute-1.amazonaws.com' % env]
    env.installed_apps = ['supervisor-gunicorn','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
    env.restart = ['gunicorn','nginx']
    env.hostname="dev-aws2"
    env.internal_ip = '10.0.0.214'

@task
def dev_admin_aws():
    common_aws()
    dev_settings()
    env.settings = "dev-admin"
    env.hosts = ['%(user)s@ip-10-0-0-244.ec2.internal' % env]
    env.installed_apps = ['supervisor-gunicorn-admin','gunicorn-admin','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
                            # Mostly involves shared servers when for example memacached is already installed.
    env.restart = ['gunicorn_admin','nginx']
    env.hostname="dev-admin"

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
    env.installed_apps = ['']
    env.hostname="scrapy"

@task
def dev_importer():
    common_aws()
    dev_settings()
    env.settings = "dev-importer-aws"
    env.hosts = ['%(user)s@ip-10-0-1-249.ec2.internal' % env]
    env.installed_apps = ['']
    env.hostname="importer"
