# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

from fab_utils import pip, get_templates, upload_template_and_reload, project, update_changed_requirements, manage
from fabric.contrib.files import exists, upload_template
from fabric.api import *
from fabric.colors import green, red

vm_bridge = True
env.solr_download_url = 'http://archive.apache.org/dist/lucene/solr/4.8.1/solr-4.8.1.tgz'
env.project_name = 'apparelrow' # no spaces!
env.app_name = 'apparelrow' # no spaces!
# environments

"""
     "supervisor-celery-background": {
        "local_path": "etc/v2/supervisor-celery-background.conf",
        "remote_path": "/etc/supervisor/conf.d/celery-background.conf",
        "reload_command": supervisor_reload_commands,
    },
     "supervisor-celerybeat": {
        "local_path": "etc/v2/supervisor-celery-beat.conf",
        "remote_path": "/etc/supervisor/conf.d/celery-beat.conf",
        "reload_command": supervisor_reload_commands,
    }
},
 "supervisor-gunicorn-admin": {
    "local_path": "etc/v2/supervisor-gunicorn-admin.conf",
    "remote_path": "/etc/supervisor/conf.d/gunicorn-admin.conf",
    "reload_command": supervisor_reload_commands,
},"""



@task
def deploy_app():
    """
    Deploy latest version of the project.
    Check out the latest version of the project from version
    control, install new requirements, sync and migrate the database,
    collect any new static assets, and restart gunicorn's work
    processes for the project.
    """
    env.use_ssh_config = True
    if not exists(env.project_path):
        prompt = raw_input("\nVirtualenv doesn't exist: %(project_name)s\nWould you like "
                           "to create it? (yes/no) " % env)
        if prompt.lower() != "yes":
            print("\nAborting!")
            return False
            # Create virtualenv
        run("virtualenv %(project_name)s --distribute" % env)
        if not exists(env.project_path):
            vcs = "git"
            run("%s clone %s %s" % (vcs, env.repo_url, env.project_path))
            pip("-r %(project_path)s/%(reqs_path)s" % env)
            pip("nodeenv")

            #with virtualenv():
            #    run("nodeenv --python-virtualenv")
            #    run("npm install -g less")
            #   run("npm install -g uglify-js")
                #run("npm install -g cssmin")
            if not exists("%(project_path)s/locale"):
                sudo("mkdir %(project_path)s/locale;chown -R %(run_user)s:%(user)s %(project_path)s/locale;chmod -R 770 %(project_path)s/locale" % env)
            run("cd %(project_path)s/%(app_name)s;ln -s static static_local" % env)
            sudo("mkdir -p %(venv_path)s/logs/emails;" % env)
            sudo("chown -R %(run_user)s:%(user)s %(venv_path)s/logs;" % env)
            sudo("chmod -R 770 %(venv_path)s/logs;" % env)
            sudo("mkdir -p %(project_path)s/%(app_name)s/media/" % env)
            sudo("chown -R %(run_user)s:%(user)s %(project_path)s/%(app_name)s/media;" % env)
            sudo("chmod -R 770 %(project_path)s/%(app_name)s/media;" % env)

    for name in get_templates():
        if not env.installed_apps or (env.installed_apps and name in env.installed_apps):
            upload_template_and_reload(name)
        else:
            print_command("%s is not activated in this install, skipping." % name)

    with project():
        # Todo reactivate this if not in RDS
        #backup("last.db")

        upload_template('apparelrow/%(settings)s.py.default' % env,'%(project_path)s/apparelrow/settings.py' % env,context=env,use_sudo=True,use_jinja=True)
        #upload_template('etc/htpasswd','%(path)s/htpasswd' % env, use_sudo=True)

        # Not the nicest of solutions but it will have to do for now. Static() is initiating the django framework which in
        # turn creates all the logfiles that do not already exist. Since those then are owned by root the run_as user will
        # not be able to write them.
        if not exists("%(venv_path)s/logs" % env):
            sudo("mkdir -p %(venv_path)s/logs;" % env)
        sudo("chown -R %(run_user)s:%(user)s %(venv_path)s/logs;chmod -R 770 %(venv_path)s/logs;" % env)

        """static_dir = static()
        env.update({'static_dir':static_dir})
        sudo("chmod -R 770 %(venv_path)s/logs/*" % env)
        if exists(static_dir):
            run("tar -cf last.tar %s" % static_dir)
        """

        git = env.git
        last_commit = "git rev-parse HEAD" if git else "hg id -i"
        run("%s > last.commit" % last_commit)
        with update_changed_requirements():
            if hasattr(env,"branch") and env.branch:
                run("git checkout %(branch)s;git pull origin %(branch)s" % env)
            else:
                run("git checkout master;git pull origin master -f")
        if not "dev" in env.settings and env.collectstatic:
            manage("collectstatic --noinput")

        #sudo("chown -R %(run_user)s:%(user)s %(static_dir)s;sudo chmod -R 770 %(static_dir)s" % env)
        #sudo("chown -R %(run_user)s:%(user)s .;sudo chmod -R 770 ." % env)
        #manage("syncdb --noinput")
        manage("migrate")
        #manage("makemessages --all")
        sudo("chown -R %(run_user)s:%(user)s %(project_path)s" % env)
    for restart_str in env.restart:
        restart(restart_str)
    return True

@task
def setup():
    sudo('apt-get install -y -q python-software-properties')
    sudo('add-apt-repository -y ppa:chris-lea/node.js')
    upload_template('etc/v2/dotdeb.org.list','/etc/apt/sources.list.d/dotdeb.org.list',use_sudo=True)
    run('wget -q -O - http://www.dotdeb.org/dotdeb.gpg | sudo apt-key add -')
    sudo('apt-get update -q')
    sudo('apt-get install -y -q build-essential python-dev python-setuptools python-virtualenv python-software-properties python-libxml2 python-libxslt1 libxml2-dev libxslt1-dev libyaml-dev libjpeg-dev libtiff-dev libpq-dev git-core curl libcurl4-gnutls-dev gettext libffi-dev mlocate apache2-utils')
    sudo('easy_install pip')

    sudo('add-apt-repository -y ppa:chris-lea/node.js')
    sudo('apt-get install -y -q nodejs')
    sudo('npm install -g less')
    sudo('npm install -g uglify-js')
    upload_template('etc/v2/boto.cfg','/etc/boto.cfg', use_sudo=True)
    sudo('chmod 744 /etc/boto.cfg')
    install_supervisor()

    #install_memcached()
    #install_redis()
    #install_gunicorn()
    #install_gunicorn_admin()
    #install_gunicorn_group()
    #install_celery()
    #deploy_app

@task
def restart(param=None):
    """
    Restart gunicorn worker processes for the project.
    """
    if param:
        sudo("supervisorctl stop %(param)s" % {'param':param})
        sudo("supervisorctl start %(param)s" % {'param':param})
    else:
        print 'No parameter supplied'
@task
def stop(param=None):
    """
    Restart gunicorn worker processes for the project.
    """
    if param:
        sudo("supervisorctl stop %(param)s" % {'param':param})
    else:
        print 'No parameter supplied'
@task
def status():
    """
    List status of all jobs running on machine.
    """
    sudo("supervisorctl status")


import os

if os.path.exists(os.path.join(os.path.dirname(__file__), "fab_install.py")):
    from fab_install import *
    green("Loading install settings", bold=True)
else:
    red("Failed to load install settings", bold=True)

if os.path.exists(os.path.join(os.path.dirname(__file__), "fab_utils.py")):
    from fab_utils import *
    green("Loading utils settings", bold=True)
else:
    red("Failed to load utils settings", bold=True)

if os.path.exists(os.path.join(os.path.dirname(__file__), "fab_servers.py")):
    from fab_servers import *
    green("Loading install settings", bold=True)
else:
    red("Failed to load server settings", bold=True)

if os.path.exists(os.path.join(os.path.dirname(__file__), "fab_servers_dev.py")):
    from fab_servers_dev import *
    green("Loading install settings", bold=True)
else:
    red("Failed to load dev server settings", bold=True)