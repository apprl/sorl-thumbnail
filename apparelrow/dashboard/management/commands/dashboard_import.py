import logging
import datetime
import pprint

from django.db.models.loading import get_model
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger('dashboard_import')


class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'

    affiliates = ['affiliatewindow', 'cj', 'linkshare', 'tradedoubler', 'zanox']

    def update(self, row):
        instance, created = get_model('dashboard', 'Sale').objects.get_or_create(affiliate=row['affiliate'], original_sale_id=row['original_sale_id'], defaults=row)

        if not created:
            for field in row.keys():
                setattr(instance, field, row.get(field))

            instance.save()

        return instance

    def handle(self, *args, **options):
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=90)

        if not args:
            args = self.affiliates

        for argument in args:
            if argument in self.affiliates:
                module = __import__('dashboard.importer.%s' % argument, fromlist = ['Importer'])
                instance = module.Importer()
                logger.info('Importing %s' % (instance.name,))
                for row in instance.get_data(start_date, end_date):
                    logger.debug('Updating row: %s' % (row,))
                    instance = self.update(row)

                    pprint.pprint(row)
