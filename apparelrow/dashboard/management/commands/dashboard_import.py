import logging
import datetime

from django.db.models.loading import get_model
from django.core.management.base import BaseCommand, CommandError

from dashboard.importer.cj import CJImporter
from dashboard.importer.linkshare import LinkshareImporter
from dashboard.importer.zanox import ZanoxImporter
#from dashboard.importer.affiliatenetwork import AffiliateWindowImporter
from dashboard.importer.tradedoubler import TradedoublerImporter

logger = logging.getLogger('dashboard_import')

import pprint

class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'

    def update(self, row):
        instance, created = get_model('dashboard', 'Sale').objects.get_or_create(original_sale_id=row['original_sale_id'], defaults=row)

        if not created:
            for field in row.keys():
                setattr(instance, field, row.get(field))

            instance.save()

        return instance

    def handle(self, *args, **options):
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=90)

        #print 'AffiliateWindow'
        #for row in AffiliateWindowImporter().get_data(start_date, end_date):
            #pprint.pprint(row)

        tradedoubler = TradedoublerImporter()
        logger.info('Importing %s' % (tradedoubler.name,))
        for row in tradedoubler.get_data(start_date, end_date):
            instance = self.update(row)

        #print 'CJ'
        #for row in CJImporter().get_data(start_date, end_date):
            #pprint.pprint(row)

        #print 'Linkshare'
        #for row in LinkshareImporter().get_data(start_date, end_date):
            #pprint.pprint(row)

        #print 'Zanox'
        #for row in ZanoxImporter().get_data(start_date, end_date):
            #pprint.pprint(row)
