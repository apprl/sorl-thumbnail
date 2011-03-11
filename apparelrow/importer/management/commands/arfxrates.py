import re, datetime, sys, urllib2
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from importer.fxrates import *

class Command(BaseCommand):
    args = "<name>"
    help = "Refresh the foreign exchange rates"
    option_list = BaseCommand.option_list + (
        make_option('--file',
            action='store',
            dest='file',
            default=None,
            help='Import the given file instead of fetching from the Internet',
        ),
        make_option('--url',
            action='store',
            dest='url',
            help='URL of file to fetch. Defaults to APPAREL_FXRATES_URL',
            default=None,
        ),
        make_option('--base_currency',
            action='store',
            dest='base_currency',
            help='ISO code of base currency to use. Defaults to APPAREL_BASE_CURRENCY',
            default=None,
        ),
    )
    
    def handle(self, *args, **options):
        kwargs = {}
        if options['file']:
            kwargs['file'] = options['file']
        elif options['url']:
            kwargs['url']  = options['url']
        else:
            kwargs['url'] = settings.APPAREL_FXRATES_URL
        
        kwargs['base_currency'] = options['base_currency'] or settings.APPAREL_BASE_CURRENCY
        
        importer = FXRateImporter(**kwargs)
        
        try:
            importer.run()
        except urllib2.HTTPError, e:
            print "Error fetching URL %s: %s" % (importer.url, e)
        except FXRateImporterParseError, e:
            print "Error parsing FX rates data: %s" % e
        else:
            print "Foreign exchange rates successfully refreshed"

