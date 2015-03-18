import datetime
import logging

from django.db.models.loading import get_model

from apparelrow.dashboard.models import Sale
from apparelrow.dashboard.importer.base import BaseImporter

logger = logging.getLogger(__name__)

class Importer(BaseImporter):

    name = 'APPRL Advertiser Network'

    def get_data(self, start_date, end_date, data=None):
        logger.info("AAN - Start importing from Transaction")
        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

        Transaction = get_model('advertiser', 'Transaction')
        Store = get_model('advertiser', 'Store')
        transactions = Transaction.objects.filter(status__in=[Transaction.ACCEPTED, Transaction.PENDING, Transaction.REJECTED]) \
                                          .filter(created__gte=start_date_query, created__lte=end_date_query)
        if transactions:
            logger.debug('Found %s transactions for AAN' % transactions.count())
        else:
            logger.debug('No transactions were found for AAN')

        for transaction in transactions:
            logger.debug('Found transaction %s.' % transaction.id)
            data_row = {}
            data_row['original_sale_id'] = '%s-%s' % (transaction.pk, transaction.order_id)
            data_row['affiliate'] = self.name
            store = Store.objects.get(identifier=transaction.store_id)
            data_row['vendor'] = store.vendor
            data_row['original_commission'] = transaction.commission
            data_row['original_currency'] = transaction.currency
            data_row['original_amount'] = transaction.order_value
            data_row['user_id'], data_row['product_id'], data_row['placement'] = self.map_placement_and_user(transaction.custom)
            data_row['sale_date'] = transaction.created
            data_row['status'] = Sale.PENDING
            if transaction.status == Transaction.ACCEPTED:
                data_row['status'] = Sale.CONFIRMED
            elif transaction.status == Transaction.REJECTED:
                data_row['status'] = Sale.DECLINED

            data_row = self.validate(data_row)
            if not data_row:
                continue

            yield data_row
