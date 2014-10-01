#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import os.path
import time

from fabric.api import *
from fabric.contrib.files import upload_template, exists
from fabtools.require.files import file as require_file
from os import environ

# globals
env.project_name = 'apparelrow' # no spaces!
env.webserver = 'nginx' # nginx or apache2 (directory name below /etc!)
env.dbserver = 'postgresql' # mysql or postgresql

#env.solr_url = 'http://apache.mirrors.spacedump.net/lucene/solr/4.5.0/solr-4.5.0.tgz'
env.solr_url = 'http://apache.cs.uu.nl/dist/lucene/solr/4.8.0/solr-4.8.0.tgz'

# environments

def localhost():
    "Use the local virtual server"
    env.hosts = ['localhost']
    env.user = 'tote'
    env.group = env.user
    env.path = '/home/tote/coding/apparelrow/apparelrow'
    env.solr_path = '/home/tote/coding/apparelrow/solr/'

def old_prod():
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
    env.gunicorn_admin_processes='2'

def old_prod_db():
    "Use our EC2 server"
    env.hosts = ['db1.apparelrow.com']
    env.user = 'deploy'
    env.db_client_host = 'ip-10-58-163-143.eu-west-1.compute.internal'
    env.datadir = '/mnt/mysql'
    env.key_filename = '%(HOME)s/.ssh/apparelrow.pem' % environ

def production_data():
    """
    Production data server, should contain solr and postgresql.
    """
    env.hosts = ['data1.apprl.com']
    env.hostname = 'data1'
    env.user = 'deploy'
    env.group = env.user
    env.path = '/home/{user}/{project_name}'.format(**env)
    env.solr_path = '/home/{user}/solr'.format(**env)

@task
def production_importer():
    """
    Production importer server.
    """
    env.hosts = ['importer1.apprl.com']
    env.hostname = 'importer1'
    env.user = 'deploy'
    env.group = env.user
    env.path = '/home/{user}/{project_name}'.format(**env)
    env.settings = 'importer'

def production_web():
    """
    Production web server.
    """
    env.hosts = ['web.apprl.com']
    env.hostname = 'web1'
    env.user = 'deploy'
    env.group = 'nogroup'
    env.run_user = 'www-data'
    env.run_group = env.run_user
    env.path = '/home/%(user)s/%(project_name)s' % env
    env.settings = 'production'
    env.celery_processes='4'
    env.celery_processes_background='3'
    env.gunicorn_processes='8'
    env.gunicorn_admin_processes='2'

def staging():
    """
    Staging web and data server.
    """
    env.hosts = ['146.185.148.124']
    env.hostname = 'staging1'
    env.user = 'deploy'
    env.group = 'nogroup'
    env.run_user = 'www-data'
    env.run_group = env.run_user
    env.path = '/home/{user}/{project_name}'.format(**env)
    env.solr_path = '/home/{user}/solr'.format(**env)
    env.settings = 'staging'
    env.celery_processes = '2'
    env.celery_processes_background = '2'
    env.gunicorn_processes = '2'
    env.gunicorn_admin_processes='1'


# tasks

def test():
    "Run the test suite and bail out if it fails"
    local("cd %(path)s; python manage.py test" % env)


def setup_data_server():
    """
    Setup a data server with both Apache Solr and PostgreSQL.
    """
    require('hosts', provided_by=[production_data, staging])
    require('path')
    require('solr_path')

    sudo('apt-get update -q')
    sudo('apt-get install -q -y openjdk-6-jre-headless')
    sudo('apt-get install -q -y postgresql-9.1 postgresql-client-9.1 postgresql-common postgresql-contrib-9.1')

    run('mkdir -p {path}'.format(**env))
    run('mkdir -p {solr_path}'.format(**env))

    install_postgresql()

    install_solr()
    deploy_solr()
    start_solr()

def setup_data_backup():
    require('hosts', provided_by=[production_data, staging])

    sudo('apt-get update -q')
    sudo('apt-get install -q -y build-essential python-dev python-pip lzop pv libevent-dev daemontools')

    # Lame, but it is easier to install it globally
    sudo('pip install wal-e')

    # TODO: encryption?
    sudo('umask u=rwx,g=rx,o=')
    sudo('mkdir -p /etc/wal-e.d/env')
    sudo('echo "VLxYKMZ09WoYL20YoKjD/d/4CJvQS+HKiWGGhJQU" > /etc/wal-e.d/env/AWS_SECRET_ACCESS_KEY')
    sudo('echo "AKIAIK3KEJCJEMGA2LTA" > /etc/wal-e.d/env/AWS_ACCESS_KEY_ID')
    sudo('echo "s3://{hostname}-database-backup/" > /etc/wal-e.d/env/WALE_S3_PREFIX'.format(**env))
    sudo('chown -R root:postgres /etc/wal-e.d')

    # Install daily cron
    put('etc/postgresql-backup.cron', '/etc/cron.d/pgbackup', use_sudo=True)
    sudo('chown root:root /etc/cron.d/pgbackup')

def setup_importer_server():
    """
    Setup importer server.
    """
    require('hosts', provided_by=[production_importer])
    require('path')

    sudo('apt-get install -y -q python-software-properties')
    sudo('apt-get update -q')
    sudo('apt-get install -y -q build-essential python-dev python-setuptools python-virtualenv libxml2-dev libxslt-dev libyaml-dev libjpeg-dev libtiff-dev libpq-dev git-core')

    run('mkdir -p %(path)s/releases %(path)s/packages %(path)s/var/logs' % env, pty=True)
    with cd(env.path):
        run('virtualenv .')
        with prefix('. bin/activate'):
            run('pip install scrapyd')
        with settings(warn_only=True):
            run('cd releases; ln -s . current; ln -s . previous;', pty=True)

@task
def deploy_importer_server(snapshot='master'):
    """
    Deploy importer server.
    """
    require('hosts', provided_by=[production_importer])
    require('path')

    # Upload all project files
    env.release = '%s-%s' % (time.strftime('%Y%m%d%H%M%S'), snapshot)
    upload_tar_from_git(snapshot)
    install_requirements()
    symlink_current_release()
    with cd(env.path):
        run('mkdir -p var/logs var/items var/dbs var/eggs')
        run('cd releases/current/apparelrow; cp %(settings)s.py.default settings.py' % env, pty=True)

    # Migrate database (XXX: should we do it here?)
    #with cd('%(path)s/releases/current' % env), prefix('. ../../bin/activate'):
    #    run('python manage.py migrate')

    # Upload scrapyd upstart and config and restart scrapyd
    upload_template(filename='etc/scrapyd.conf', destination='%(path)s/releases/current/spiderpig/scrapy.cfg' % env, context=env, use_sudo=False, use_jinja=True)
    upload_template(filename='etc/scrapyd.upstart', destination='/etc/init/scrapyd.conf', context=env, use_sudo=True, use_jinja=True)
    sudo('service scrapyd restart')

    # Upload crons
    upload_template('etc/run_spiders.cron', '/etc/cron.d/run_spiders', context=env, use_sudo=True, backup=False)
    sudo('chown root:root /etc/cron.d/run_spiders', pty=True)
    sudo('chmod 0644 /etc/cron.d/run_spiders', pty=True)

    # Deploy spiderpig project
    with cd(os.path.join(env.path, 'releases', 'current', 'spiderpig')), prefix('. ../../../bin/activate'):
        run('scrapyd-deploy spidercrawl -p spidercrawl')


# OLD SETUP DATABASE CODE
#def setup_db():
    #"""
    #Setup a DB server
    #"""
    #require('hosts', provided_by=[localhost])
    #require('path')
    #sudo('apt-get update')
    #if env.dbserver=='mysql':
        #sudo('apt-get install -y mysql-server')
        #sudo('stop mysql')
        #sudo('test -d /var/lib/mysql && mv /var/lib/mysql /mnt || true')
        #sudo("sed -i 's/var\/lib/mnt/' /etc/apparmor.d/usr.sbin.mysqld")
        #upload_template('etc/mysql.cnf', '/etc/mysql/conf.d/apparelrow.cnf', use_sudo=True, context=env)
        #sudo('/etc/init.d/apparmor restart')
        #sudo('start mysql')
        #upload_template('etc/mysql.sql', '/tmp/setup.sql', context=env)
        #sudo('mysql -u root -p < /tmp/setup.sql')
        #sudo('restart mysql')
    #elif env.dbserver=='postgresql':
        #sudo('apt-get install -y postgresql')
        #upload_template('etc/postgres.sql', '/tmp/setup.sql', context=env)
        #sudo('psql < /tmp/setup.sql', user='postgres')
        #sudo('/etc/init.d/postgresql-8.4 restart')
    #sudo('rm -f /tmp/setup.sql')

def setup(snapshot='master'):
    """
    Setup a fresh virtualenv as well as a few useful directories, then run
    a full deployment
    """
    require('hosts', provided_by=[localhost])
    require('path')
    # install Python environment
    sudo('apt-get install -y -q python-software-properties')
    sudo('add-apt-repository -y ppa:chris-lea/node.js')
    sudo('apt-get update -q')
    sudo('apt-get install -y -q build-essential python-dev python-setuptools python-virtualenv python-libxml2 python-libxslt1 libxml2-dev libxslt1-dev libyaml-dev libjpeg-dev libtiff-dev libpq-dev git-core')

    # install memcached
    sudo('apt-get install -y -q memcached')
    # install lessc
    sudo('apt-get install -y -q nodejs')
    sudo('npm install -g less')
    sudo('npm install -g uglify-js')

    # install more Python stuff
    # Don't install setuptools or virtualenv on Ubuntu with easy_install or pip! Only Ubuntu packages work!
    sudo('easy_install pip')

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
            run('mkdir -m a+w -p var/logs; mkdir -m a+w -p var/hprof; mkdir -p etc releases shared/warehouse shared/static/products packages backup;', pty=True)
            sudo('chown -R %(run_user)s:%(run_group)s var shared/warehouse shared/static shared/static/products;' % env, pty=True)
            run('cd releases; ln -s . current; ln -s . previous;', pty=True)
    install_redis()
    # Disabled because it is no longer used by the importer
    #install_parallel()
    deploy('first', snapshot=snapshot)
    # Disabled, should run load fixtures manually when starting with a fresh database which is not always the case
    #load_fixtures()

def deploy(param='', snapshot='master'):
    """
    Deploy the latest version of the site to the servers, install any
    required third party modules, install the virtual host and
    then restart the webserver
    """
    require('hosts', provided_by=[localhost,production_web])
    require('path')
    env.release = '%s-%s' % (time.strftime('%Y%m%d%H%M%S'), snapshot)
    upload_tar_from_git(snapshot)
    install_requirements()
    install_webserver()
    install_gunicorn()
    copy_bin()
    copy_config()
    build_styles_and_scripts()
    migrate(param)
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
    require('hosts', provided_by=[localhost,production_web])
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
    require('hosts', provided_by=[localhost,production_web])
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
    require('path', 'gunicorn_processes', 'gunicorn_admin_processes')
    with cd(env.path):
        upload_template('etc/gunicorn-server' % env, '%(path)s/bin' % env, context=env, use_sudo=True)
        sudo('chmod a+x %(path)s/bin/gunicorn-server' % env, pty=True)

def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        with prefix('. bin/activate'):
            #run('curl https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py | python')
            run('pip install -U -r ./releases/%(release)s/etc/requirements.pip' % env, pty=True)

def copy_bin():
    require('release', provided_by=[deploy, setup])
    run('cd %(path)s; cp ./releases/%(release)s/bin/* ./bin' % env, pty=True)

def copy_config():
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        run('cp ./releases/%(release)s/etc/* ./etc' % env, pty=True)
        run('cp ./releases/%(release)s/etc/requirements.pip ./etc/requirements.pip' %env, pty=True)
        run('cd releases/%(release)s/apparelrow; cp %(settings)s.py.default settings.py' % env, pty=True)
        sudo('cp ./releases/%(release)s/etc/redis.conf /etc/redis.conf' % env, pty=True)
        sudo('cp ./releases/%(release)s/etc/crontab /etc/crontab' % env, pty=True)
        sudo('cp ./releases/%(release)s/etc/celeryd.init /etc/init.d/celeryd' % env, pty=True)

    upload_template('etc/logrotate.conf', '/etc/logrotate.d/apparelrow', context=env, use_sudo=True, backup=False)
    upload_template('etc/arimport.cron', '/etc/cron.daily/arimport', context=env, use_sudo=True)
    sudo('chmod a+x /etc/cron.daily/arimport', pty=True)
    upload_template('etc/availability.cron', '/etc/cron.weekly/availability', context=env, use_sudo=True)
    sudo('chmod a+x /etc/cron.weekly/availability', pty=True)
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

    # vendor check cron
    upload_template('etc/vendor_check.cron', '/etc/cron.daily/vendor_check', context=env, use_sudo=True)
    sudo('chmod a+x /etc/cron.daily/vendor_check', pty=True)

    # django cleanup cron
    upload_template('etc/django_cleanup.cron', '/etc/cron.weekly/django_cleanup', context=env, use_sudo=True)
    sudo('chmod a+x /etc/cron.weekly/django_cleanup', pty=True)

def build_styles_and_scripts():
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s/%(project_name)s' % env):
        sudo('chown -R %(run_user)s:%(run_group)s ./static' % env, pty=True)
        #sudo('cd ./sass; /var/lib/gems/1.8/bin/compass compile' % env, pty=True, user=env.run_user)
        run('mkdir -p media', pty=True)
        sudo('chown -R %(run_user)s:%(run_group)s ./media' % env, pty=True)
        sudo('ln -s ../../../../shared/static media/static', pty=True, user=env.run_user)
        with prefix('. ../../../bin/activate'):
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

def restart_celeryd():
    sudo('/etc/init.d/celeryd restart', pty=False)

def restart_memcached():
    sudo('/etc/init.d/memcached restart', pty=False)

def restart_webserver():
    "Restart the web server"
    require('webserver')
    with settings(warn_only=True):
        sudo('service %(webserver)s start' % env, pty=False)
        sudo('service %(webserver)s reload' % env, pty=False)

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


#
# PostgreSQL commands
#

def install_postgresql():
    # TODO: setup pg_hba.conf (currently done manually)
    put('etc/postgresql.conf.{hostname}'.format(**env),
        '/etc/postgresql/9.1/main/postgresql.conf', use_sudo=True)
    sudo('chown postgres:postgres /etc/postgresql/9.1/main/postgresql.conf')

    put('etc/postgres.sql', '/tmp/setup_postgres.sql')
    sudo('psql < /tmp/setup_postgres.sql', user='postgres')
    sudo('rm -f /tmp/setup_postgres.sql')

    restart_postgresql()

def migrate_to_postgresql():
    run('rm -f apparelrow_migrate.mysql')
    run('ssh deploy@db1.apparelrow.com mysqldump --compatible=postgresql --default-character-set=utf8 -u root apparelrow -p > apparelrow_migrate.mysql')
    run('wget https://raw.github.com/lanyrd/mysql-postgresql-converter/master/db_converter.py')
    run('python db_converter.py apparelrow_migrate.mysql apparelrow_migrate.psql')
    run('psql -h localhost -U apparel -d apparel -f apparelrow_migrate.psql')
    run('rm -f db_converter.py')

def start_postgresql():
    sudo('service postgresql start')

def stop_postgresql():
    sudo('service postgresql stop')

def restart_postgresql():
    sudo('service postgresql restart')

def status_postgresql():
    sudo('service postgresql service')


#
# Solr commands
#

def install_solr():
    solr_tgz = os.path.basename(env.solr_url)
    solr_dirname, _ = os.path.splitext(solr_tgz)

    require_file(url=env.solr_url, path=os.path.join(env.solr_path, solr_tgz))

    with cd(env.solr_path):
        run('tar xf {0}'.format(solr_tgz))
        run('rsync -a --remove-source-files {0}/ solr'.format(solr_dirname))
        run('rm -r {0}'.format(solr_dirname))
        # Only update currency.xml to our default version on setup
        put('etc/solr-currency.xml', os.path.join(env.solr_path, 'solr', 'example', 'solr', 'collection1', 'conf', 'currency.xml'))

    copy_upstart_solr()


def copy_upstart_solr():
    context = {'user': env.user,
               'group': env.user,
               'path': os.path.join(env.solr_path, 'solr', 'example')}
    upload_template(filename='etc/solr.upstart', destination='/etc/init/solr.conf', context=context, use_sudo=True, use_jinja=True)


def status_solr():
    run('service solr status')
    run('wget -O - http://localhost:8983/solr/admin/cores?action=STATUS')


def restart_solr():
    with settings(warn_only=True):
        sudo('service solr restart')


def start_solr():
    if not 'running' in run('service solr status'):
        sudo('service solr start')


def stop_solr():
    sudo('service solr stop')


def deploy_solr():
    require('solr_path')

    put('etc/solr-solrconfig.xml', os.path.join(env.solr_path, 'solr', 'example', 'solr', 'collection1', 'conf', 'solrconfig.xml'))
    put('etc/solr-schema.xml', os.path.join(env.solr_path, 'solr', 'example', 'solr', 'collection1', 'conf', 'schema.xml'))
    put('etc/solr-synonyms.txt', os.path.join(env.solr_path, 'solr', 'example', 'solr', 'collection1', 'conf', 'synonyms.txt'))
    put('etc/solr.properties', os.path.join(env.solr_path, 'solr', 'example', 'solr', 'collection1', 'core.properties'))

    currency_path = os.path.join(env.solr_path, 'solr', 'example', 'solr', 'collection1', 'conf', 'currency.xml')
    if not exists(currency_path):
        put('etc/solr-currency.xml', currency_path)

    if 'running' in run('service solr status'):
        run('wget -O - http://localhost:8983/solr/admin/cores?action=RELOAD')


if os.path.exists(os.path.join(os.path.dirname(__file__), "fab_local.py")):
    from fab_local import *