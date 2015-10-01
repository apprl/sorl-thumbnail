import logging
from advertiser.models import Transaction
from django.db.models.loading import get_model

from django.core.management.base import BaseCommand
logger = logging.getLogger('dashboard')


class Command(BaseCommand):

    def handle(self, *args, **options):
        for vendor in get_model('apparel', 'Vendor').objects.all():
            if vendor.is_cpc:
                try:
                    store = get_model('advertiser', 'Store').objects.get(vendor=vendor)
                    store_id = store.identifier
                except get_model('advertiser', 'Store').DoesNotExist:
                    store_id = None

                if store_id:
                    sales = get_model('dashboard', 'Sale').objects.filter(affiliate='cost_per_click', vendor=vendor)
                    for row in sales:
                        transaction = get_model('advertiser', 'Transaction').objects.filter(order_id=row.original_sale_id)
                        if len(transaction) == 0:
                            defaults = {
                                'ip_address': '127.0.0.1',
                                'status': Transaction.ACCEPTED,
                                'cookie_date': row.sale_date,
                                'currency': row.currency,
                                'original_currency': row.original_currency,
                                'exchange_rate': row.exchange_rate,
                                'order_value': row.converted_amount,
                                'commission': row.converted_commission,
                                'original_order_value': row.original_amount,
                                'original_commission': row.original_commission,
                            }
                            transaction, created = Transaction.objects.get_or_create(store_id=store_id,
                                                                               order_id=row.original_sale_id, defaults=defaults)
                            if created:
                                logger.warning("Transaction has been created for existent sale %s." % row.id)
