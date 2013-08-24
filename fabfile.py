#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import with_statement # needed for python 2.5
from fabric.api import *
from fabric.contrib.files import upload_template
from os import environ

# globals
env.project_name = 'apparelrow' # no spaces!
env.webserver = 'nginx' # nginx or apache2 (directory name below /etc!)
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
    env.settings = 'production'
    env.key_filename = '%(HOME)s/.ssh/apparelrow.pem' % environ
    env.celery_processes='4'
    env.celery_processes_background='3'
    env.gunicorn_processes='3'

def prod_db():
    "Use our EC2 server"
    env.hosts = ['db1.apparelrow.com']
    env.user = 'deploy'
    env.db_client_host = 'ip-10-58-163-143.eu-west-1.compute.internal'
    env.datadir = '/mnt/mysql'
    env.key_filename = '%(HOME)s/.ssh/apparelrow.pem' % environ

def staging():
    env.hosts = ['ec2-176-34-85-220.eu-west-1.compute.amazonaws.com']
    env.hostname = 'staging1'
    env.user = 'deploy'
    env.group = 'nogroup'
    env.run_user = 'www-data'
    env.run_group = env.run_user
    env.path = '/mnt/%(project_name)s' % env
    env.settings = 'staging'
    env.db_client_host = 'localhost'
    env.datadir = '/mnt/mysql'
    env.key_filename = '%(HOME)s/.ssh/apparelrow.pem' % environ
    env.celery_processes='2'
    env.celery_processes_background='2'
    env.gunicorn_processes='2'

# tasks

def test():
    "Run the test suite and bail out if it fails"
    local("cd %(path)s; python manage.py test" % env)

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
    # install lessc
    sudo('apt-get install -y node-less')

    # install more Python stuff
    # Don't install setuptools or virtualenv on Ubuntu with easy_install or pip! Only Ubuntu packages work!
    sudo('easy_install pip')

    # Install Compass
    #sudo('apt-get install -y rubygems')
    #sudo('gem install compass --no-rdoc --no-ri')

    if env.dbserver=='mysql':
        sudo('apt-get install -y libmysqlclient-dev')
    elif env.dbserver=='postgresql':
        sudo('apt-get install -y python-psycopg2')
    if env.webserver=='lighttpd':
        sudo('apt-get install -y lighttpd')
    elif env.webserver=='nginx':
        sudo('apt-get install -y nginx')

    # disable default site
    with settings(warn_only=True):
        sudo('cd /etc/%(webserver)s/conf-enabled/; rm -f default;' % env, pty=True)
        sudo('cd /etc/%(webserver)s/sites-enabled/; rm -f default;' % env, pty=True)

    # new project setup
    sudo('mkdir -p %(path)s; chown %(user)s:%(group)s %(path)s;' % env, pty=True)
    with cd(env.path):
        run('virtualenv --no-site-packages .')
        with settings(warn_only=True):
            run('mkdir -m a+w -p var/logs; mkdir -p etc releases shared/warehouse packages backup;', pty=True)
            sudo('chown -R %(run_user)s:%(run_group)s var shared/warehouse;' % env, pty=True)
            run('cd releases; ln -s . current; ln -s . previous;', pty=True)
    install_redis()
    install_parallel()
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
    env.release = '%s-%s' % (time.strftime('%Y%m%d%H%M%S'), snapshot)
    upload_tar_from_git(snapshot)
    install_requirements()
    install_webserver()
    install_gunicorn()
    copy_bin()
    copy_config()
    copy_solr()
    build_styles_and_scripts()
    migrate(param)
    build_brand_list()
    copy_sitemap()
    symlink_current_release()
    restart_celeryd()
    restart_gunicorn()
    # No need to restart memcache on every deploy, better to do it manually if
    # needed with fab server restart_memcached
    #restart_memcached()
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
        sudo('%(path)s/bin/python ../manage.py loaddata importer/fixtures/color_mapping.yaml importer/fixtures/feedvendors.yaml apparel/fixtures/*' % env, pty=True, user=env.run_user)

def upload_tar_from_git(snapshot='master'):
    "Create an archive from the current Git master branch and upload it"
    require('release', provided_by=[deploy, setup])
    env.snapshot=snapshot
    local('git archive --format=tar %(snapshot)s | gzip > %(release)s.tar.gz' % env)
    run('mkdir -p %(path)s/releases/%(release)s' % env, pty=True)
    put('%(release)s.tar.gz' % env, '%(path)s/packages/' % env)
    run('cd %(path)s/releases/%(release)s && tar zxf ../../packages/%(release)s.tar.gz' % env, pty=True)
    local('rm %(release)s.tar.gz' % env)

def install_webserver():
    require('release', provided_by=[deploy, setup])
    if env.webserver == 'lighttpd':
        install_lighttpd()
    elif env.webserver == 'nginx':
        install_nginx()

def install_lighttpd():
    upload_template('etc/%(webserver)s.conf.%(hostname)s' % env, '/etc/%(webserver)s/conf-available/%(project_name)s.conf' % env, context=env, use_sudo=True)
    upload_template('etc/%(webserver)s.conf.include' % env, '/etc/%(webserver)s/conf-available/%(project_name)s.include.conf' % env, context=env, use_sudo=True)
    with settings(warn_only=True):
        sudo('cd /etc/%(webserver)s/conf-enabled/; ln -sf ../conf-available/%(project_name)s.conf %(project_name)s.conf' % env, pty=True)

def install_nginx():
    upload_template('etc/nginx.conf.%(hostname)s' % env, '/etc/nginx/sites-available/%(project_name)s.conf' % env, context=env, use_sudo=True)
    upload_template('etc/nginx.conf.include' % env, '/etc/nginx/sites-available/%(project_name)s.include.conf' % env, context=env, use_sudo=True)
    with settings(warn_only=True):
        sudo('cd /etc/nginx/sites-enabled/; ln -sf ../sites-available/%(project_name)s.conf %(project_name)s.conf' % env, pty=True)

def install_gunicorn():
    require('path', 'gunicorn_processes')
    with cd(env.path):
        upload_template('etc/gunicorn-server' % env, '%(path)s/bin' % env, context=env, use_sudo=True)
        sudo('chmod a+x %(path)s/bin/gunicorn-server' % env, pty=True)

def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        with prefix('. bin/activate'):
            run('pip install -U -r ./releases/%(release)s/etc/requirements.pip' % env, pty=True)

def copy_bin():
    require('release', provided_by=[deploy, setup])
    run('cd %(path)s; cp ./releases/%(release)s/bin/* ./bin' % env, pty=True)

def copy_solr():
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        sudo('cp -rup ./releases/%(release)s/solr/ .' % env, pty=True)
        sudo('chown --silent -R %(run_user)s:%(run_group)s ./solr' % env, pty=True)
        sudo('touch ./solr/solr/collection1/conf/synonyms.txt', user=env.run_user, pty=True)

    # Make sure currency.xml is created for solr
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        sudo('%(path)s/bin/python ../manage.py arfxrates --no_update --solr' % env, pty=True, user=env.run_user)

def copy_config():
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        run('cp ./releases/%(release)s/etc/* ./etc' % env, pty=True)
        run('cp ./releases/%(release)s/etc/requirements.pip ./etc/requirements.pip' %env, pty=True)
        run('cp ./etc/logging.conf.default ./etc/logging.conf' % env, pty=True)
        run('cd releases/%(release)s/apparelrow; cp %(settings)s.py.default settings.py' % env, pty=True)
        sudo('cp ./releases/%(release)s/etc/redis.conf /etc/redis.conf' % env, pty=True)
        sudo('cp ./releases/%(release)s/etc/crontab /etc/crontab' % env, pty=True)
        sudo('cp ./releases/%(release)s/etc/celeryd.init /etc/init.d/celeryd' % env, pty=True)

    upload_template('etc/logrotate.conf', '/etc/logrotate.d/apparelrow', context=env, use_sudo=True)
    upload_template('etc/arimport.cron', '/etc/cron.daily/arimport', context=env, use_sudo=True)
    sudo('chmod a+x /etc/cron.daily/arimport', pty=True)
    upload_template('etc/availability.cron', '/etc/cron.weekly/availability', context=env, use_sudo=True)
    sudo('chmod a+x /etc/cron.weekly/availability', pty=True)
    upload_template('etc/solr.conf.init', '/etc/init/solr.conf', context=env, use_sudo=True)
    upload_template('etc/celeryd.default', '/etc/default/celeryd', context=env, use_sudo=True)
    sudo('update-rc.d celeryd defaults', pty=True)
    upload_template('etc/redis.init', '/etc/init/redis.conf', context=env, use_sudo=True)

    # popularity cron
    upload_template('etc/apparel_popularity.cron', '/etc/cron.weekly/apparel_popularity', context=env, use_sudo=True)
    sudo('chmod a+x /etc/cron.weekly/apparel_popularity', pty=True)

    # dashboard crons
    upload_template('etc/dashboard_import.cron', '/etc/cron.daily/aa_dashboard_import', context=env, use_sudo=True)
    sudo('chmod a+x /etc/cron.daily/aa_dashboard_import', pty=True)
    upload_template('etc/dashboard_payment.cron', '/etc/cron.monthly/dashboard_payment', context=env, use_sudo=True)
    sudo('chmod a+x /etc/cron.monthly/dashboard_payment', pty=True)

def build_styles_and_scripts():
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        sudo('chown -R %(run_user)s:%(run_group)s ./static' % env, pty=True)
        #sudo('cd ./sass; /var/lib/gems/1.8/bin/compass compile' % env, pty=True, user=env.run_user)
        run('mkdir media', pty=True)
        sudo('chown -R %(run_user)s:%(run_group)s ./media' % env, pty=True)
        sudo('ln -s ../../../../shared/static media/static', pty=True, user=env.run_user)
        sudo('%(path)s/bin/python ../manage.py collectstatic --noinput' % env, pty=True, user=env.run_user)

def migrate_s3():
    """
    NO LONGER USED
    """
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        # XXX: running thumbnail clear/cleanup requires lots of ram
        #sudo('%(path)s/bin/python ../manage.py thumbnail clear' % env, pty=True, user=env.run_user)
        #sudo('%(path)s/bin/python ../manage.py thumbnail cleanup' % env, pty=True, user=env.run_user)
        sudo('%(path)s/bin/python ../manage.py sync_media_s3 -d %(path)s/shared/static -p static' % env, pty=True, user=env.run_user)

def symlink_current_release():
    "Symlink our current release"
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        run('rm releases/previous; mv releases/current releases/previous;', pty=True)
        run('ln -s %(release)s releases/current' % env, pty=True)

def copy_sitemap():
    """Copy sitemap from previous release to current"""
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        sudo('chown -R %(run_user)s:%(run_group)s ./sitemaps' % env, pty=True)

    # Copy sitemap files from current before it is symlinked
    with cd('%(path)s/releases/' % env), settings(warn_only=True):
        sudo('cp -p ./current/%(project_name)s/sitemaps/* ./%(release)s/%(project_name)s/sitemaps/' % env, pty=True)

def migrate(param=''):
    "Update the database"
    require('project_name')
    require('path')
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        if param=='first':
            sudo('%(path)s/bin/python ../manage.py syncdb' % env, pty=True, user=env.run_user)
            # Migrate in specific order
            sudo('%(path)s/bin/python ../manage.py migrate apparel' % env, pty=True, user=env.run_user)
            sudo('%(path)s/bin/python ../manage.py migrate profile' % env, pty=True, user=env.run_user)
        sudo('%(path)s/bin/python ../manage.py migrate' % env, pty=True, user=env.run_user)

def install_redis():
    run('mkdir -p /tmp/redis', pty=True)
    env.redis_release = 'redis-2.4.17'
    with cd('/tmp/redis'):
        run('wget http://redis.googlecode.com/files/%(redis_release)s.tar.gz' % env, pty=True)
        run('tar zxf %(redis_release)s.tar.gz' % env, pty=True)
        with cd(env.redis_release):
            run('make', pty=True)
            sudo('make install', pty=True)
    sudo('adduser --system redis', pty=True)
    sudo('mkdir -p /var/lib/redis /var/log/redis', pty=True)
    sudo('chown redis /var/lib/redis /var/log/redis', pty=True)

def install_parallel():
    run('mkdir -p /tmp/parallel', pty=True)
    env.parallel_release = 'parallel-20120822'
    with cd('/tmp/parallel'):
        run('wget -O- http://ftp.gnu.org/gnu/parallel/%(parallel_release)s.tar.bz2 | tar jxf -' % env, pty=True)
        with cd(env.parallel_release):
            run('./configure', pty=True)
            run('make', pty=True)
            sudo('make install', pty=True)

def restart_django():
    require('path')
    with cd(env.path):
        sudo('./bin/django-server restart', pty=False, user=env.run_user)

def restart_gunicorn():
    require('path')
    with cd(env.path):
        sudo('./bin/gunicorn-server', pty=False, user=env.run_user)

def restart_solr():
    with settings(warn_only=True):
        sudo('restart solr', pty=False)

def restart_celeryd():
    sudo('/etc/init.d/celeryd restart', pty=False)

def restart_memcached():
    sudo('/etc/init.d/memcached restart', pty=False)

def restart_webserver():
    "Restart the web server"
    require('webserver')
    with settings(warn_only=True):
        # Temporary to migrate from lighttpd to nginx
        if env.webserver == 'nginx':
            sudo('/etc/init.d/lighttpd stop' % env, pty=False)
            sudo('/etc/init.d/nginx start' % env, pty=False)
        sudo('/etc/init.d/%(webserver)s reload' % env, pty=False)

def build_brand_list():
    """Build static brand list"""
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        sudo('chown -R %(run_user)s:%(run_group)s ./templates/apparel/generated/' % env, pty=True)
        sudo('%(path)s/bin/python ../manage.py build_brand_list' % env, pty=True, user=env.run_user)

def manage_py(command):
    env.manage_py_command = command
    with cd('%(path)s/releases/current/%(project_name)s' % env):
        sudo('%(path)s/bin/python ../manage.py %(manage_py_command)s' % env, pty=True, user=env.run_user)
