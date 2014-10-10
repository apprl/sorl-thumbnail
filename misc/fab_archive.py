# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'
from django.utils.translation import ugettext_lazy as _

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


