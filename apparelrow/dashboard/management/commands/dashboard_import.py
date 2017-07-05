import datetime
import logging
import optparse

from django.core.management.base import BaseCommand

from apparelrow.dashboard.models import Sale

logger = logging.getLogger('affiliate_networks')


class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'
    option_list = BaseCommand.option_list + (
        optparse.make_option('--days',
            action='store',
            dest='days',
            help='Start date set to current date - selected number of days',
            default=90,
        ),optparse.make_option('--data',
            action='store',
            dest='data',
            default=None,
        ),
    )

    affiliates = ['affiliatewindow', 'cj', 'linkshare', 'tradedoubler', 'zanox', 'aan']

    def update(self, row):
        # Creates a sale only if the vendor supports Cost per order

        if row['vendor'] and row['vendor'].is_cpo:
            instance, created = Sale.objects.get_or_create(affiliate=row['affiliate'], original_sale_id=row['original_sale_id'], defaults=row)

            # If we have an existing pending Sale - update it. This will cause its UserEarnings to be recreated
            # by the Sale save signal
            if not created and instance.paid == Sale.PAID_PENDING:
                for field in row.keys():
                    setattr(instance, field, row.get(field))
                instance.save()

            return instance

    def handle(self, *args, **options):
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=int(options.get('days')))
        data = options.get('data')

        if not args:
            args = self.affiliates

        for argument in args:
            if argument in self.affiliates:
                module = __import__('apparelrow.dashboard.importer.%s' % argument, fromlist = ['Importer'])
                instance = module.Importer()
                logger.info('Importing %s' % (instance.name,))
                try:
                    for row in instance.get_data(start_date, end_date, data):
                        logger.debug('Updating row: %s' % (row,))
                        sale_instance = self.update(row)
                except Exception as e:
                    logger.exception('Failed to import %s for interval %s-%s' % (instance.name, start_date, end_date))
