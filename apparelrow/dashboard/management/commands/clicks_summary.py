import optparse
import datetime
import logging
from advertiser.models import Transaction
from django.db.models.loading import get_model

from django.core.management.base import BaseCommand

logger = logging.getLogger('dashboard')


class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'
    option_list = BaseCommand.option_list + (
        optparse.make_option('--date',
            action='store',
            dest='date',
            help='Select a custom date in the format YYYY-MM-DD',
            default= None,
        ),
    )

    def update(self, row):
        instance, created = get_model('dashboard', 'Sale').objects.get_or_create(affiliate=row['affiliate'], original_sale_id=row['original_sale_id'], defaults=row)
        if row['store_id']:
            defaults = {
                'ip_address': '127.0.0.1',
                'status': Transaction.ACCEPTED,
                'cookie_date': instance.sale_date,
                'currency': instance.currency,
                'original_currency': instance.original_currency,
                'exchange_rate': instance.exchange_rate,
                'order_value': instance.converted_amount,
                'commission': instance.converted_commission,
                'original_order_value': instance.original_amount,
                'original_commission': instance.original_commission,
            }
            transaction, _ = Transaction.objects.get_or_create(store_id=row['store_id'],
                                                               order_id=row['original_sale_id'], defaults=defaults)

        if not created and instance.paid == get_model('dashboard', 'Sale').PAID_PENDING:
            for field in row.keys():
                setattr(instance, field, row.get(field))
            instance.save()
        logger.info("Earning per click with sale id %s for user %s updated " % (instance.id, instance.user_id))
        return instance


    def handle(self, *args, **options):
        date = options.get('date')
        if not date:
            date = (datetime.date.today() - datetime.timedelta(1)).strftime('%Y-%m-%d')
        query_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        module = __import__('apparelrow.dashboard.importer.costperclick', fromlist = ['Importer'])
        instance = module.Importer()
        logger.info('Importing %s' % (instance.name,))
        for row in instance.get_data(query_date, None):
            sale_instance = self.update(row)