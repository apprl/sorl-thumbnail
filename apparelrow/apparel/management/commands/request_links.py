# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'


from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os
import requests
import time

debug = True

class Command(BaseCommand):
    args = ''
    help = 'Takes a file containing links to all new or updated products and calls them.'

    def handle(self, *args, **options):
        counter = 0
        bad_counter = 0
        try:
            file_path = os.path.join(settings.PROJECT_ROOT, '..', '..', 'var', 'logs', 'pending_requests.log')
            print 'Opening file %s for reading.' % file_path
            request_file = open(file_path, "r")
            try:
                lines = request_file.readlines()
                print 'Found %s lines of requests to be made.' % len(lines)
                for line in lines:
                    try:
                        print 'Requesting %s' % line
                        start = time.time()
                        if not line.startswith('http'):
                            line = 'http://apprl.com%s' % line
                        r = requests.get('%s' % line)
                        print 'Finished request in:%s s' % (time.time() - start)
                    except Exception,msg:
                        print 'Failed to request [%s] due to %s.' % (line,msg)
            except Exception,msg:
                print 'An error has occured: %s' % msg
            finally:
                request_file.close()
                if not debug:
                    os.remove(file_path)
                print 'Closing and removing file.'
        except IOError,msg:
            print 'Error opening file: %s' % msg