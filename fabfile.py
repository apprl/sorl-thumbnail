#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import with_statement # needed for python 2.5
from fabric.api import *
from fabric.contrib.files import upload_template
from os import environ

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

def demo():
    "Use the actual webserver"
    env.hosts = ['demo.apparelrow.com:32744']
    env.user = 'hanssonlarsson'
    env.group = env.user
    env.run_user = 'www-data'
    env.run_group = env.run_user
    env.path = '/home/%(user)s/%(project_name)s' % env

def prod():
    "Use our EC2 server"
    env.hosts = ['web1.apparelrow.com']
    env.user = 'deploy'
    env.group = 'nogroup'
    env.run_user = 'www-data'
    env.run_group = env.run_user
    env.path = '/home/%(user)s/%(project_name)s' % env
    env.key_filename = '%(HOME)s/.ssh/apparelrow.pem' % environ

def prod_db():
    "Use our EC2 server"
    env.hosts = ['db1.apparelrow.com']
    env.user = 'deploy'
    env.datadir = '/mnt/mysql'
    env.key_filename = '%(HOME)s/.ssh/apparelrow.pem' % environ
   
# tasks

def test():
    "Run the test suite and bail out if it fails"
    local("cd %(path)s; python manage.py test --settings production" % env)
    
def setup_db():
    """
    Setup a DB server
    """
    require('hosts', provided_by=[localhost,demo,prod_db])
    require('path')
    sudo('apt-get update')
    if env.dbserver=='mysql':
        sudo('apt-get install -y mysql-server')
        sudo('stop mysql')
        sudo('test -d /var/lib/mysql && mv /var/lib/mysql /mnt || true')
        sudo("sed -i 's/var\/lib/mnt/' /etc/apparmor.d/usr.sbin.mysqld")
        upload_template('etc/mysql.cnf', '/etc/mysql/conf.d/apparelrow.cnf', use_sudo=True, context=env)
        sudo('/etc/init.d/apparmor restart')
        sudo('start mysql')
        upload_template('etc/mysql.sql', '/tmp/setup.sql', context=env)
        sudo('mysql -u root -p < /tmp/setup.sql')
        sudo('restart mysql')
    elif env.dbserver=='postgresql':
        sudo('apt-get install -y postgresql')
        upload_template('etc/postgres.sql', '/tmp/setup.sql', context=env)
        sudo('psql -U root -W < /tmp/setup.sql')
        sudo('restart postgresql')
    sudo('rm -f /tmp/setup.sql')
    
def setup(snapshot='master'):
    """
    Setup a fresh virtualenv as well as a few useful directories, then run
    a full deployment
    """
    require('hosts', provided_by=[localhost,demo,prod])
    require('path')
    # install Python environment
    sudo('apt-get update')
    sudo('apt-get install -y build-essential python-dev python-setuptools python-virtualenv libxml2-dev libxslt1-dev')
    # install some version control systems, since we need Django modules in development
    sudo('apt-get install -y git-core subversion')
    # install rabbitmq-server (add http://www.rabbitmq.com/debian.html#apt for newest version)
    sudo('apt-get install -y rabbitmq-server')
    # install memcached
    sudo('apt-get install -y memcached')
    # install java (for solr)
    sudo('apt-get install -y openjdk-6-jre-headless')

    # install more Python stuff
    # Don't install setuptools or virtualenv on Ubuntu with easy_install or pip! Only Ubuntu packages work!
    sudo('easy_install pip')

    # Install Compass
    sudo('apt-get install -y rubygems')
    sudo('gem install compass --no-rdoc --no-ri')

    if env.dbserver=='mysql':
        sudo('apt-get install -y libmysqlclient-dev')
    elif env.dbserver=='postgresql':
        sudo('apt-get install -y python-psycopg2')
    if env.webserver=='lighttpd':
        sudo('apt-get install -y lighttpd')
        
    # disable default site
    with settings(warn_only=True):
        sudo('cd /etc/%(webserver)s/conf-enabled/; rm default;' % env, pty=True)
    
    # new project setup
    sudo('mkdir -p %(path)s; chown %(user)s:%(group)s %(path)s;' % env, pty=True)
    with cd(env.path):
        run('virtualenv --no-site-packages .')
        with settings(warn_only=True):
            run('mkdir -m a+w -p var/logs; mkdir -p etc releases shared packages backup;', pty=True)
            sudo('chown -R %(run_user)s:%(run_group)s var;' % env, pty=True)
            run('cd releases; ln -s . current; ln -s . previous;', pty=True)
    deploy('first', snapshot=snapshot)
    
def deploy(param='', snapshot='master'):
    """
    Deploy the latest version of the site to the servers, install any
    required third party modules, install the virtual host and 
    then restart the webserver
    """
    require('hosts', provided_by=[localhost,demo,prod])
    require('path')
    import time
    env.release = time.strftime('%Y%m%d%H%M%S')
    upload_tar_from_git(snapshot)
    install_requirements()
    install_site()
    copy_bin()
    copy_solr()
    copy_config()
    build_styles_and_scripts()
    migrate(param)
    symlink_current_release()
    restart_solr()
    restart_celeryd()
    restart_django()
    restart_memcached()
    restart_webserver()
    
def deploy_version(version):
    "Specify a specific version to be made live"
    require('hosts', provided_by=[localhost,demo,prod])
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
    require('hosts', provided_by=[localhost,demo,prod])
    require('path')
    with cd(env.path):
        run('mv releases/current releases/_previous;', pty=True)
        run('mv releases/previous releases/current;', pty=True)
        run('mv releases/_previous releases/previous;', pty=True)
        # TODO: use South to migrate back
    restart_webserver()    
    
# Helpers. These are called by other functions rather than directly

def upload_tar_from_git(snapshot='master'):
    "Create an archive from the current Git master branch and upload it"
    require('release', provided_by=[deploy, setup])
    env.snapshot=snapshot
    local('git archive --format=tar %(snapshot)s | gzip > %(release)s.tar.gz' % env)
    run('mkdir -p %(path)s/releases/%(release)s' % env, pty=True)
    put('%(release)s.tar.gz' % env, '%(path)s/packages/' % env)
    run('cd %(path)s/releases/%(release)s && tar zxf ../../packages/%(release)s.tar.gz' % env, pty=True)
    local('rm %(release)s.tar.gz' % env)
    
def install_site():
    "Add the virtualhost config file to the webserver's config, activate logrotate"
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s' % env):
        upload_template('etc/%(webserver)s.conf.default' % env, '/etc/%(webserver)s/conf-available/%(project_name)s.conf' % env, context=env, use_sudo=True)
    with settings(warn_only=True):
        sudo('cd /etc/%(webserver)s/conf-enabled/; ln -s ../conf-available/%(project_name)s.conf %(project_name)s.conf' % env, pty=True)
    
def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=[deploy, setup])
    run('cd %(path)s; pip install -E . -r ./releases/%(release)s/etc/requirements.pip' % env, pty=True)

def copy_bin():
    require('release', provided_by=[deploy, setup])
    run('cd %(path)s; cp -n ./releases/%(release)s/bin/* ./bin' % env, pty=True)

def copy_solr():
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        sudo('cp -rup ./releases/%(release)s/solr/ .' % env, pty=True)
        sudo('chown --silent -R %(run_user)s:%(run_group)s ./solr' % env, pty=True)

def copy_config():
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        run('cp -n ./releases/%(release)s/etc/* ./etc' % env, pty=True)
        run('cp ./releases/%(release)s/etc/requirements.pip ./etc/requirements.pip' %env, pty=True)
        run('cp -n ./etc/logging.conf.default ./etc/logging.conf' % env, pty=True)
        run('cd releases/%(release)s/apparelrow; cp production.py.default production.py' % env, pty=True)
        upload_template('etc/arimport.cron', '/etc/cron.daily/arimport', context=env, use_sudo=True)
        sudo('chmod a+x /etc/cron.daily/arimport', pty=True)
        upload_template('etc/solr.conf.init', '/etc/init/solr.conf', context=env, use_sudo=True)
        upload_template('etc/celeryd.default', '/etc/default/celeryd', context=env, use_sudo=True)
        sudo('cp -n ./releases/%(release)s/etc/celeryd.init /etc/init.d/celeryd' % env, pty=True)
        sudo('update-rc.d celeryd defaults', pty=True)

def build_styles_and_scripts():
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        sudo('chown -R %(run_user)s:%(run_group)s ./media' % env, pty=True)
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

def restart_solr():
    with settings(warn_only=True):
        sudo('restart solr', pty=True)

def restart_celeryd():
    sudo('/etc/init.d/celeryd restart', pty=True)

def restart_memcached():
    sudo('/etc/init.d/memcached restart', pty=True)

def restart_webserver():
    "Restart the web server"
    require('webserver')
    with settings(warn_only=True):
        sudo('/etc/init.d/%(webserver)s reload' % env, pty=True)
