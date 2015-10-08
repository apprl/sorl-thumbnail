import re
import datetime
import sys
import urllib2
import logging
import subprocess
from optparse import make_option
from xml.etree import ElementTree
from xml.etree.cElementTree import Element, SubElement
from xml.dom import minidom
import requests

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apparelrow.importer.fxrates import *
from apparelrow.apparel.models import VendorProduct

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
        make_option('--solr',
            action='store_true',
            dest='solr',
            help='Save currency data to currency.xml in Solr',
            default=False,
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

        if options['solr']:
            cmd = True
            self.generate_currency_xml_file(**options)

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
            except FXRate.DoesNotExist:
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

    def generate_currency_xml_file(self, **options):
        rates = {}
        currencies = []
        for rate in FXRate.objects.filter(base_currency=options['base_currency']).order_by('currency').values('currency', 'rate'):
            rates[rate['currency']] = rate['rate']
            currencies.append(rate['currency'])

        root_element = Element('currencyConfig')
        root_element.set('version', '1.0')
        rates_element = SubElement(root_element, 'rates')

        for x in currencies:
            for y in currencies:
                if x == y:
                    continue

                rate = rates[y] * (1 / rates[x])
                if x == options['base_currency']:
                    rate = rates[y]
                elif y == options['base_currency']:
                    rate = 1 / rates[x]

                rate_element = SubElement(rates_element, 'rate')
                rate_element.set('from', x)
                rate_element.set('to', y)
                rate_element.set('rate', str(rate))

        rough_string = ElementTree.tostring(root_element, 'utf-8')
        reparsed = minidom.parseString(rough_string)

        if settings.SOLR_CURRENCY_LOCAL:
            with open(settings.SOLR_CURRENCY_FILE, 'w') as f:
                f.write(reparsed.toprettyxml(indent='  '))
        else:
            p = subprocess.Popen(['ssh', '-o', 'UserKnownHostsFile=/home/deploy/www-data-ssh/known_hosts', '-i', '/home/deploy/www-data-ssh/id_rsa', settings.SOLR_SSH_STRING, 'cat - > {0}'.format(settings.SOLR_CURRENCY_FILE)], stdin=subprocess.PIPE)
            p.stdin.write(reparsed.toprettyxml(indent='  '))
            p.stdin.close()
            p.wait()
            if p.returncode != 0:
                raise Exception('Could not find path to file {0} on {1}'.format(settings.SOLR_CURRENCY_FILE, settings.SOLR_SSH_STRING))


        # This try is required because solr might not be running during a
        # deploy and when we generate currency.xml it is not possible to reload
        # what is not running...
        try:
            requests.get(settings.SOLR_RELOAD_URL)
        except requests.exceptions.RequestException:
            logging.error('Could not reload solr core after currency.xml update')
