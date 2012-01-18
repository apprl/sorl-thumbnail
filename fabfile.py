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
    env.hostname = 'web1'
    env.user = 'deploy'
    env.group = 'nogroup'
    env.run_user = 'www-data'
    env.run_group = env.run_user
    env.path = '/home/%(user)s/%(project_name)s' % env
    env.config = 'production'
    env.key_filename = '%(HOME)s/.ssh/apparelrow.pem' % environ

def prod_db():
    "Use our EC2 server"
    env.hosts = ['db1.apparelrow.com']
    env.user = 'deploy'
    env.db_client_host = 'ip-10-250-227-75.eu-west-1.compute.internal'
    env.datadir = '/mnt/mysql'
    env.key_filename = '%(HOME)s/.ssh/apparelrow.pem' % environ

def staging():
    env.hosts = ['staging1.apparelrow.com']
    env.hostname = 'staging1'
    env.user = 'deploy'
    env.group = 'nogroup'
    env.run_user = 'www-data'
    env.run_group = env.run_user
    env.path = '/mnt/%(project_name)s' % env
    env.config = 'staging'
    env.db_client_host = 'localhost'
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
        sudo('psql < /tmp/setup.sql', user='postgres')
        sudo('/etc/init.d/postgresql-8.4 restart')
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
    sudo('apt-get install -y build-essential python-dev python-setuptools python-virtualenv libxml2-dev libxslt1-dev libyaml-dev libjpeg-dev libtiff-dev')
    # install some version control systems, since we need Django modules in development
    sudo('apt-get install -y git-core subversion')
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
        sudo('cd /etc/%(webserver)s/conf-enabled/; rm -f default;' % env, pty=True)
    
    # new project setup
    sudo('mkdir -p %(path)s; chown %(user)s:%(group)s %(path)s;' % env, pty=True)
    with cd(env.path):
        run('virtualenv --no-site-packages .')
        with settings(warn_only=True):
            run('mkdir -m a+w -p var/logs; mkdir -p etc releases shared/warehouse shared/static packages backup;', pty=True)
            sudo('chown -R %(run_user)s:%(run_group)s var shared/warehouse shared/static;' % env, pty=True)
            run('cd releases; ln -s . current; ln -s . previous;', pty=True)
    install_redis()
    deploy('first', snapshot=snapshot)
    load_fixtures()
    
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

def load_fixtures():
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        sudo('%(path)s/bin/python manage.py loaddata importer/fixtures/color_mapping.yaml importer/fixtures/feedvendors.yaml apparel/fixtures/* --settings production' % env, pty=True, user=env.run_user)

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
        sudo('touch ./solr/solr/conf/synonyms.txt', user=env.run_user, pty=True)

def copy_config():
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        run('cp -n ./releases/%(release)s/etc/* ./etc' % env, pty=True)
        run('cp ./releases/%(release)s/etc/requirements.pip ./etc/requirements.pip' %env, pty=True)
        run('cp -n ./etc/logging.conf.default ./etc/logging.conf' % env, pty=True)
        run('cd releases/%(release)s/apparelrow; cp %(config)s.py.default production.py' % env, pty=True)
        upload_template('etc/logrotate.conf', '/etc/logrotate.d/apparelrow', context=env, use_sudo=True)
        upload_template('etc/arimport.cron', '/etc/cron.daily/arimport', context=env, use_sudo=True)
        sudo('chmod a+x /etc/cron.daily/arimport', pty=True)
        upload_template('etc/solr.conf.init', '/etc/init/solr.conf', context=env, use_sudo=True)
        upload_template('etc/celeryd.default', '/etc/default/celeryd', context=env, use_sudo=True)
        sudo('cp -n ./releases/%(release)s/etc/celeryd.init /etc/init.d/celeryd' % env, pty=True)
        sudo('update-rc.d celeryd defaults', pty=True)
        upload_template('etc/redis.init', '/etc/init/redis.conf', context=env, use_sudo=True)
        sudo('cp -n ./releases/%(release)s/etc/redis.conf /etc/redis.conf' % env, pty=True)

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
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        if param=='first':
            sudo('%(path)s/bin/python manage.py syncdb --settings production' % env, pty=True, user=env.run_user)
            # Migrate in specific order
            sudo('%(path)s/bin/python manage.py migrate apparel --settings production' % env, pty=True, user=env.run_user)
            sudo('%(path)s/bin/python manage.py migrate profile --settings production' % env, pty=True, user=env.run_user)
        sudo('%(path)s/bin/python manage.py migrate --settings production' % env, pty=True, user=env.run_user)
    
def install_redis():
    run('mkdir -p /tmp/redis', pty=True)
    env.redis_release = 'redis-2.4.6'
    with cd('/tmp/redis'):
        run('wget http://redis.googlecode.com/files/%(redis_release)s.tar.gz' % env, pty=True)
        run('tar zxf %(redis_release)s.tar.gz' % env, pty=True)
        with cd(env.redis_release):
            run('make', pty=True)
            sudo('make install', pty=True)
    sudo('adduser --system redis', pty=True)
    sudo('mkdir -p /var/lib/redis /var/log/redis', pty=True)
    sudo('chown redis /var/lib/redis /var/log/redis', pty=True)

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
