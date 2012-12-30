from django.core.management.base import BaseCommand, CommandError

from dashboard.importer.cj import CJImporter
from dashboard.importer.linkshare import LinkshareImporter
from dashboard.importer.zanox import ZanoxImporter
#from dashboard.importer.affiliatenetwork import AffiliateWindowImporter
from dashboard.importer.tradedoubler import TradedoublerImporter

import pprint

class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'

    def handle(self, *args, **options):
        #print 'AffiliateWindow'
        #for row in AffiliateWindowImporter().get_data():
            #pprint.pprint(row)

        print 'Tradedoubler'
        for row in TradedoublerImporter().get_data():
            pprint.pprint(row)

        print 'CJ'
        for row in CJImporter().get_data():
            pprint.pprint(row)

        print 'Linkshare'
        for row in LinkshareImporter().get_data():
            pprint.pprint(row)

        print 'Zanox'
        for row in ZanoxImporter().get_data():
            pprint.pprint(row)
