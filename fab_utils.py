# -*- coding: utf-8 -*-
from fab_servers_dev import dev_scrapy

__author__ = 'klaswikblad'

import os
from contextlib import contextmanager
from fabric.decorators import task
from fabric.contrib.files import exists, upload_template
from fabric.colors import yellow, green, blue, red
from fabric.api import *

def _print(output):
    print()
    print(output)
    print()


def print_command(command):
    _print(blue("$ ", bold=True) +
           yellow(command, bold=True) +
           red(" ->", bold=True))


def static():
    """
    Returns the live STATIC_ROOT directory.
    """
    return python("from django.conf import settings;"
                  "print settings.STATIC_ROOT", show=False).split("\n")[-1]

@task
def manage(command):
    """
    Runs a Django management command.
    """
    return run("%s %s" % (env.manage, command))

@task
def python(code, show=True):
    """
    Runs Python code in the project's virtual environment, with Django loaded.
    """
    setup = "import os; os.environ[\'DJANGO_SETTINGS_MODULE\']=\'apparelrow.settings\';" % env
    full_code = 'python -c "%s%s"' % (setup, code.replace("`", "\\\`"))
    with project():
        result = run(full_code)
        if show:
            print_command(code)
    return result


@task
def pip(packages):
    """
    Installs one or more Python packages within the virtual environment.
    """
    with virtualenv():
        return run("pip install %s" % packages)

@contextmanager
def virtualenv():
    """
    Runs commands within the project's virtualenv.
    """
    with cd(env.venv_path):
        with prefix("source %s/bin/activate" % env.venv_path):
            yield

@contextmanager
def project():
    """
    Runs commands within the project's directory.
    """
    with virtualenv():
        with cd(env.project_dirname):
            yield

@contextmanager
def update_changed_requirements():
    """
    Checks for changes in the requirements file across an update,
    and gets new requirements if changes have occurred.
    """
    import os
    reqs_path = os.path.join(env.project_path, env.reqs_path)
    get_reqs = lambda: run("cat %s" % reqs_path)
    old_reqs = get_reqs() if env.reqs_path else ""
    yield
    if old_reqs:
        new_reqs = get_reqs()
        if old_reqs == new_reqs:
            # Unpinned requirements should always be checked.
            for req in new_reqs.split("\n"):
                if req.startswith("-e"):
                    if "@" not in req:
                        # Editable requirement without pinned commit.
                        break
                elif req.strip() and not req.startswith("#"):
                    if not set(">=<") & set(req):
                        # PyPI requirement without version.
                        break
            else:
                # All requirements are pinned.
                return
        pip("-r %s/%s" % (env.project_path, env.reqs_path))

@task
def _run(command, show=True):
    """
    Runs a shell comand on the remote server.
    """
    if show:
        print_command(command)
    with hide("running"):
        return _run(command)

def get_templates():
    """
    Returns each of the templates with env vars injected.
    """
    injected = {}
    if os.path.exists(os.path.join(os.path.dirname(__file__), "fab_apps.py")):
        from fab_apps import templates
        injected = {}
        for name, data in templates.items():
            injected[name] = dict(
                                [(k, [val % env for val in v] if k == "reload_command" else v % env)
                                   for k, v in data.items()])
            green("Found and loaded template %s" % name, bold=True)
    else:
        red("Unable to find defined apps.", bold=True)
    return injected


def upload_template_and_reload(name):
    """
    Uploads a template only if it has changed, and if so, reload a
    related service.
    """
    import os
    import re
    template = get_templates()[name]
    _print(template)
    local_path = template["local_path"] % env
    if not os.path.exists(local_path):
        project_root = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(project_root, local_path)
    remote_path = template["remote_path"]
    reload_command = template.get("reload_command")
    owner = template.get("owner")
    mode = template.get("mode")
    remote_data = ""
    if exists(remote_path):
        with hide("stdout"):
            remote_data = sudo("cat %s" % remote_path)
    with open(local_path, "r") as f:
        local_data = f.read()
        # Escape all non-string-formatting-placeholder occurrences of '%':
        local_data = re.sub(r"%(?!\(\w+\)s)", "%%", local_data)
        if "%(db_pass)s" in local_data:
            env.db_pass = 'notset' #dbpass()
        local_data %= env
    clean = lambda s: s.replace("\n", "").replace("\r", "").strip()
    if clean(remote_data) == clean(local_data):
        return
    upload_template(local_path, remote_path, env, use_sudo=True, backup=False)
    if owner:
        sudo("chown %s %s" % (owner, remote_path))
    if mode:
        sudo("chmod %s %s" % (mode, remote_path))
    sudo('chown -R %(run_user)s:%(user)s %(venv_path)s/logs;chmod -R 770 %(venv_path)s/logs' % env)
    if reload_command:
        for command in reload_command:
            sudo(command)


def postgres(command):
    """
    Runs the given command as the postgres user.
    """
    from fabfile import run
    show = not command.startswith("psql")
    return run("%s" % command)
    #return run("sudo -u root sudo -u postgres %s" % command)


def backup(filename=None):
    """
    Backs up the database.
    """
    from fabfile import env
    #return postgres("pg_dump -h apprlvm -Fc apprl > %s" % (env.project_name, filename))
    if not filename:
        filename="last.db"
    env.update({'filename':filename})
    return postgres("pg_dump -U %(db_user)s -h %(db_url)s -Fc %(db_name)s > %(filename)s" % env)


def restore(filename):
    """
    Restores the database.
    """
    env.update({'filename':filename})
    return postgres("pg_restore -c -d %(db_name)s %(filename)s" % env )

@task
def collectstatic():
    with project():
        sudo("python manage.py collectstatic -v 0 --noinput", user="%(run_user)s" % env)

@task
def scrape(vendor):
    require('hostname', provided_by=[dev_scrapy])
    with project():
        run("curl http://localhost:6800/schedule.json -d project=spidercrawl -d spider=%(vendor)s" % {'vendor':vendor})

@task
def reload_scrapy():
    if env.reload_scrapy:
        with project():
            with cd("spiderpig"):
                run("scrapyd-deploy spidercrawl -p spidercrawl")

@task
def scrape(vendor):
    require('hostname', provided_by=[dev_scrapy])
    with project():
        run("curl http://localhost:6800/schedule.json -d project=spidercrawl -d spider=%(vendor)s" % {'vendor':vendor})

@task
def minorupdate():
    sudo("apt-get update;apt-get upgrade")

@task
def scrapingstatus():
    run("sh get_stats.sh")

@task
def importer(vendor):
    with project():
        sudo ("python manage.py run_importer --vendor=%(vendor)s" % {"vendor":vendor}, user="%(run_user)s" % env)
