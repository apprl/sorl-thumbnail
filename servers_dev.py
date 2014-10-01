# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'
from django.utils.translation import ugettext_lazy as _

from fabric.api import *
from servers import common_aws


def localhost():
    "Use the local virtual server"
    env.hosts = ['localhost']
    env.user = 'klaswikblad'
    env.group = env.user
    env.path = '/Users/%(user)s/PycharmProjects/apparelenv/apparelrow/' % env
    env.solr_path = '/Users/%(user)s/PycharmProjects/apparelenv/apparelrow/solr-apprl/' % env

@task
def dev_web_aws_1():
    common_aws()
    env.settings = 'dev-aws'
    env.hosts = ['ec2-54-165-249-140.compute-1.amazonaws.com']
    env.installed_apps = ['supervisor-gunicorn','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
                            # Mostly involves shared servers when for example memacached is already installed.

    ## local urls ##
    env.db_url = "apprldbinstance.cirbmil58ncc.us-east-1.rds.amazonaws.com"
    env.solr_url = "ip-10-0-1-247.ec2.internal"
    env.s3_url = "s-staging"
    env.memcached_path = "apprl-cache-cluster.naojmu.cfg.use1.cache.amazonaws.com"
    env.redis_url = "ip-10-0-1-249.ec2.internal"

    env.hostname="dev-aws1"
    env.internal_ip = "10.0.0.213"

@task
def dev_web_aws_2():
    common_aws()
    env.settings = 'dev-aws'
    env.hosts = ['ec2-54-165-249-190.compute-1.amazonaws.com']
    env.installed_apps = ['supervisor-gunicorn','gunicorn','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
                            # Mostly involves shared servers when for example memacached is already installed.
    env.db_url = "apprldbinstance.cirbmil58ncc.us-east-1.rds.amazonaws.com"
    env.solr_url = "ip-10-0-1-247.ec2.internal"
    env.s3_url = "s-staging"
    env.memcached_path = "apprl-cache-cluster.naojmu.cfg.use1.cache.amazonaws.com"
    env.redis_url = "ip-10-0-1-249.ec2.internal"

    env.hostname="dev-aws2"
    env.internal_ip = '10.0.0.214'

@task
def dev_aws_admin():
    common_aws()
    env.hosts = ['ec2-54-77-127-96.eu-west-1.compute.amazonaws.com']
    env.installed_apps = ['supervisor-gunicorn-admin','gunicorn-admin','nginx-basic-v2','nginx-application','supervisor-nginx',] # Empty means everything. Depends on what else is already on the server at the time.
                            # Mostly involves shared servers when for example memacached is already installed.
    env.hostname="admin"
    env.settings = 'production-admin'

