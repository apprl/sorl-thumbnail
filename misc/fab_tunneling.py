# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'
from django.utils.translation import ugettext_lazy as _

from fabric.api import *
from fabric.contrib.console import confirm
from time import time
import subprocess, shlex, atexit, time
from os import remove

env.use_ssh_config = True
env.context = 'local'
remote_user = 'deploy'
tunnels = []

class SSHTunnel:
    def __init__(self, bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, timeout=15):
        self.local_port = local_port
        cmd = 'ssh -vAN -L %d:%s:%d %s@%s' % (local_port, dest_host, dest_port, bridge_user, bridge_host)
        self.p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        start_time = time.time()
        atexit.register(self.p.kill)
        while not 'Entering interactive session' in self.p.stderr.readline():
            if time.time() > start_time + timeout:
                raise "SSH tunnel timed out"
    def entrance(self):
        return 'localhost:%d' % self.local_port

@task
def test_live():
    env.user = 'deploy'
    prod = SSHTunnel(remote_user, 'dev-bastion', 'scraper')
    env.hosts = [prod.entrance()]
    run('ls -al')



env.hosts = ['deploy@scraper']

@task
def dothis():
    env.forward_agent = True
    env.user = "deploy"
    with cd('%(venv_path)s/logs/' % env):
        sudo('tail -f theimp.log')
