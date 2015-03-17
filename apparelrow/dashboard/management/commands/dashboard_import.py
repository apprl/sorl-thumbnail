import logging
import datetime
import optparse

from django.db.models.loading import get_model
from django.core.management.base import BaseCommand

logger = logging.getLogger('dashboard.import')


class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'
    option_list = BaseCommand.option_list + (
        optparse.make_option('--days',
            action='store',
            dest='days',
            help='Start date set to current date - selected number of days',
            default=90,
        ),
    )

    affiliates = ['affiliatewindow', 'cj', 'linkshare', 'tradedoubler', 'zanox', 'aan']

    def update(self, row):
        # Creates a sale only if the vendor supports Cost per order
        if row['vendor'].is_cpo:
            instance, created = get_model('dashboard', 'Sale').objects.get_or_create(affiliate=row['affiliate'], original_sale_id=row['original_sale_id'], defaults=row)

            if not created and instance.paid == get_model('dashboard', 'Sale').PAID_PENDING:
                for field in row.keys():
                    setattr(instance, field, row.get(field))

            instance.save()

            return instance

    def handle(self, *args, **options):
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=int(options.get('days')))

        if not args:
            args = self.affiliates

        for argument in args:
            if argument in self.affiliates:
                module = __import__('apparelrow.dashboard.importer.%s' % argument, fromlist = ['Importer'])
                instance = module.Importer()
                logger.info('Importing %s' % (instance.name,))
                try:
                    for row in instance.get_data(start_date, end_date):
                        logger.debug('Updating row: %s' % (row,))
                        sale_instance = self.update(row)
                except Exception as e:
                    logger.exception('Failed to import %s for interval %s-%s' % (instance.name, start_date, end_date))
