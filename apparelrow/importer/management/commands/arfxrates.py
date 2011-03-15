import re, datetime, sys, urllib2
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from importer.fxrates import *
from apparel.models import VendorProduct

class Command(BaseCommand):
    args = "<name>"
    help = "Manage currency exchange rate import and conversion"
    option_list = BaseCommand.option_list + (
        make_option('--refresh',
            action='store_true',
            dest='refresh',
            default=False,
            help='Refresh exchanges stored in database before updating prices',
        ),
        make_option('--no_update',
            action='store_true',
            dest='no_update',
            default=False,
            help='Run other commands, but do not updated prices',
        ),
        
        make_option('--currency',
            action='store',
            dest='currency',
            help='Only update prices in this currency',
            default=None,
        ),
        make_option('--file',
            action='store',
            dest='file',
            default=None,
            help='Import the given rates file instead of fetching from the Internet',
        ),
        make_option('--url',
            action='store',
            dest='url',
            help='URL of file to rates fetch. Defaults to APPAREL_FXRATES_URL',
            default=settings.APPAREL_FXRATES_URL,
        ),
        make_option('--base_currency',
            action='store',
            dest='base_currency',
            help='ISO code of base currency to use when. Defaults to APPAREL_BASE_CURRENCY',
            default=settings.APPAREL_BASE_CURRENCY,
        ),
    )
    
    def handle(self, *args, **options):
        kwargs = {}
        cmd = False
        
        if options['refresh']:
            cmd = True
            self.refresh_rates(**options)
        
        if not options['no_update']:
            cmd = True
            self.update_prices(**options)
         
        if not cmd:
            raise CommandError('Nothing to do')
    
    
    def refresh_rates(self, **options):
        kwargs = {}
        
        if options['file']:
            kwargs['file'] = options['file']
        else:
            kwargs['url']  = options['url']
        
        kwargs['base_currency'] = options['base_currency']
        
        importer = FXRateImporter(**kwargs)
        
        try:
            importer.run()
        except urllib2.HTTPError, e:
            raise CommandError("Error fetching URL %s: %s" % (importer.url, e))
        except FXRateImporterParseError, e:
            raise CommandError("Error parsing FX rates data: %s" % e)
        else:
            print "Foreign exchange rates successfully refreshed"
    
    def update_prices(self, **options):
        
        fxrates = None
        
        if options['currency']:
            try:
                fxrates = [
                    FXRate.objects.get(
                        base_currency=options['base_currency'],
                        currency=options['currency']
                    )
                ]
            except FXRates.DoesNotExist:
                raise CommandError('No fx rate matching base currency %s and currency %s' % (
                    options['base_currency'],
                    options['currency']
                ))
        else:
            fxrates = FXRate.objects.filter(
                currency__in=VendorProduct.objects.all().distinct('original_currency').values_list('original_currency', flat=True),
                base_currency=options['base_currency']
            )
            if len(fxrates) == 0:
                raise CommandError('No fx rate matching base currency %s' % options['base_currency'])
        
        
        for fxrate in fxrates:
            fxrate.update_prices() 
        
        print "Prices successfully updated"
