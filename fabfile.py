#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import with_statement # needed for python 2.5
from fabric.api import *

# globals
env.project_name = 'apparelrow' # no spaces!
env.webserver = 'lighttpd' # nginx or apache2 (directory name below /etc!)
env.dbserver = 'mysql' # mysql or postgresql

# environments

def localhost():
    "Use the local virtual server"
    env.hosts = ['localhost']
    env.user = 'linus'
    env.path = '/home/%(user)s/development/projects/%(project_name)s' % env
    env.virtualhost_path = env.path

def demo():
    "Use the actual webserver"
    env.hosts = ['demo.apparelrow.com:32744']
    env.user = 'hanssonlarsson'
    env.run_user = 'www-data'
    env.path = '/home/hanssonlarsson/%(project_name)s' % env
    env.virtualhost_path = env.path
   
# tasks

def test():
    "Run the test suite and bail out if it fails"
    local("cd %(path)s; python manage.py test --settings production" % env)
    
    
def setup():
    """
    Setup a fresh virtualenv as well as a few useful directories, then run
    a full deployment
    """
    require('hosts', provided_by=[localhost,demo])
    require('path')
    # install Python environment
    sudo('apt-get update')
    sudo('apt-get install -y build-essential python-dev python-setuptools python-virtualenv libxml2-dev libxslt1-dev')
    # install some version control systems, since we need Django modules in development
    sudo('apt-get install -y git-core subversion')
    # install rabbitmq-server (add http://www.rabbitmq.com/debian.html#apt for newest version)
    sudo('apt-get install rabbitmq-server')
        
    # install more Python stuff
    # Don't install setuptools or virtualenv on Ubuntu with easy_install or pip! Only Ubuntu packages work!
    sudo('easy_install pip')

    if env.webserver=='lighttpd':
        sudo('apt-get install -y lighttpd')
    if env.dbserver=='mysql':
        sudo('apt-get install -y mysql-server libmysqlclient-dev')
    elif env.dbserver=='postgresql':
        sudo('apt-get install -y postgresql python-psycopg2')
        
    # disable default site
    with settings(warn_only=True):
        sudo('cd /etc/%(webserver)s/conf-enabled/; rm default;' % env, pty=True)
    
    # new project setup
    sudo('mkdir -p %(path)s; chown %(user)s:%(user)s %(path)s;' % env, pty=True)
    with cd(env.path):
        run('virtualenv --no-site-packages .')
        with settings(warn_only=True):
            run('mkdir -m a+w -p var/logs; mkdir -p etc releases shared packages backup;', pty=True)
            sudo('chown -R %(run_user)s:%(run_user)s var;' % env, pty=True)
            run('cd releases; ln -s . current; ln -s . previous;', pty=True)
    deploy('first')
    
def deploy(param=''):
    """
    Deploy the latest version of the site to the servers, install any
    required third party modules, install the virtual host and 
    then restart the webserver
    """
    require('hosts', provided_by=[localhost,demo])
    require('path')
    import time
    env.release = time.strftime('%Y%m%d%H%M%S')
    upload_tar_from_git()
    install_requirements()
    install_site()
    copy_bin()
    copy_config()
    build_styles_and_scripts()
    migrate(param)
    symlink_current_release()
    restart_celeryd()
    restart_django()
    restart_webserver()
    
def deploy_version(version):
    "Specify a specific version to be made live"
    require('hosts', provided_by=[localhost,demo])
    require('path')
    env.version = version
    with cd(env.path):
        run('rm -rf releases/previous; mv releases/current releases/previous;', pty=True)
        run('ln -s %(version)s releases/current' % env, pty=True)
    restart_webserver()
    
def rollback():
    """
    Limited rollback capability. Simply loads the previously current
    version of the code. Rolling back again will swap between the two.
    """
    require('hosts', provided_by=[localhost,demo])
    require('path')
    with cd(env.path):
        run('mv releases/current releases/_previous;', pty=True)
        run('mv releases/previous releases/current;', pty=True)
        run('mv releases/_previous releases/previous;', pty=True)
        # TODO: use South to migrate back
    restart_webserver()    
    
# Helpers. These are called by other functions rather than directly

def upload_tar_from_git():
    "Create an archive from the current Git master branch and upload it"
    require('release', provided_by=[deploy, setup])
    local('git archive --format=tar master | gzip > %(release)s.tar.gz' % env)
    run('mkdir -p %(path)s/releases/%(release)s' % env, pty=True)
    put('%(release)s.tar.gz' % env, '%(path)s/packages/' % env)
    run('cd %(path)s/releases/%(release)s && tar zxf ../../packages/%(release)s.tar.gz' % env, pty=True)
    local('rm %(release)s.tar.gz' % env)
    
def install_site():
    "Add the virtualhost config file to the webserver's config, activate logrotate"
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s' % env):
        sudo('cp etc/%(webserver)s.conf.default /etc/%(webserver)s/conf-available/%(project_name)s.conf' % env, pty=True)
    with settings(warn_only=True):
        sudo('cd /etc/%(webserver)s/conf-enabled/; ln -s ../conf-available/%(project_name)s.conf %(project_name)s.conf' % env, pty=True)
    
def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=[deploy, setup])
    run('cd %(path)s; pip install -E . -r ./releases/%(release)s/etc/requirements.pip' % env, pty=True)

def copy_bin():
    require('release', provided_by=[deploy, setup])
    run('cd %(path)s; cp -n ./releases/%(release)s/bin/* ./bin' % env, pty=True)

def copy_config():
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        run('cp -n ./releases/%(release)s/etc/* ./etc' % env, pty=True)
        run('cp -n ./etc/logging.conf.default ./etc/logging.conf' % env, pty=True)
        run('cd releases/%(release)s/apparelrow; cp production.py.default production.py' % env, pty=True)
        sudo('cp -n ./releases/%(release)s/etc/arimport.cron /etc/cron.daily/arimport' % env, pty=True)
        sudo('cp -n ./releases/%(release)s/etc/celeryd.default /etc/default/celeryd' % env, pty=True)
        sudo('cp -n ./releases/%(release)s/etc/celeryd.init /etc/init.d/celeryd' % env, pty=True)
        sudo('update-rc.d celeryd defaults', pty=True)

def build_styles_and_scripts():
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        sudo('chown -R %(run_user)s:%(run_user)s ./media' % env, pty=True)
        sudo('%(path)s/bin/python manage.py synccompress --settings production' % env, pty=True, user=env.run_user)
        sudo('cd ./media; /var/lib/gems/1.8/bin/compass compile' % env, pty=True, user=env.run_user)
        sudo('ln -s ../../../../shared/static media/static', pty=True, user=env.run_user)
        sudo('ln -s ../../../../../lib/python2.6/site-packages/tinymce/media/tiny_mce media/js/tiny_mce', pty=True, user=env.run_user)

    
def symlink_current_release():
    "Symlink our current release"
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        run('rm releases/previous; mv releases/current releases/previous;', pty=True)
        run('ln -s %(release)s releases/current' % env, pty=True)
    
def migrate(param=''):
    "Update the database"
    require('project_name')
    require('path')
    env.southparam = '--auto'
    if param=='first':
        sudo('cd %(path)s/releases/%(release)s/%(project_name)s; %(path)s/bin/python manage.py syncdb --noinput --settings production' % env, pty=True, user=env.run_user)
        env.southparam = '--initial'
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        #run('%(path)s/bin/python manage.py schemamigration %(project_name)s %(southparam)s --settings production && %(path)s/bin/python manage.py migrate %(project_name)s --settings production' % env)
        sudo('%(path)s/bin/python manage.py migrate --settings production' % env, pty=True, user=env.run_user)
        # TODO: should also migrate other apps! get migrations from previous releases
    
def restart_django():
    require('path')
    with cd(env.path):
        sudo('./bin/django-server restart', pty=True, user=env.run_user)

def restart_celeryd():
    sudo('/etc/init.d/celeryd restart', pty=True)

def restart_webserver():
    "Restart the web server"
    require('webserver')
    with settings(warn_only=True):
        sudo('/etc/init.d/%(webserver)s reload' % env, pty=True)
