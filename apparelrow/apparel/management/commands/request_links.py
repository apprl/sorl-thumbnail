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
                        request_line = line.split(' ')
                        if not len(request_line) == 5:
                            continue
                        product_url = request_line[4]
                        print 'Requesting %s' % product_url
                        start = time.time()
                        if not product_url.startswith('http'):
                            product_url = 'http://apprl.com%s' % product_url
                        r = requests.get('%s' % product_url)
                        counter += 1
                        print '%s:Finished request in:%s s' % (counter,time.time() - start)
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