import requests
import datetime
import xmltodict
import math
import decimal
import dateutil.parser
import logging

from dashboard.models import Sale
from dashboard.importer.base import BaseImporter

logger = logging.getLogger(__name__)

class Importer(BaseImporter):

    name = 'CJ'
    api_key = '008765b01c28856695bf9e6d1cf5a964c828bd64e087f52702d89cf427ba83cdeba00854d1b2ed9151887662aad9d9871c15a21e7bc0d97214d51648835c533a33/7ff6c059ec861fad39dbce3e0783a02778317f8ca19235db7fc3df11493ad6bb1189e6776f22d162c90449ae44dd21331c04606bf8d3aee2e4645f7de06b6571'

    def get_data(self, start_date, end_date):
        for start_date, end_date in self.generate_subdates(start_date, end_date, 30):
            headers = {'authorization': self.api_key}
            url = 'https://commission-detail.api.cj.com/v3/commissions?date-type=posting&start-date=%s&end-date=%s' % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            response = requests.get(url, headers=headers)
            data = xmltodict.parse(response.text)
            if int(data['cj-api']['commissions']['@total-matched']) > 0:
                for row in data['cj-api']['commissions']['commission']:
                    data_row = {}
                    data_row['original_sale_id'] = row['original-action-id']
                    data_row['affiliate'] = self.name
                    _, data_row['vendor'] = self.map_vendor(row['advertiser-name'])
                    data_row['original_commission'] = row['commission-amount']
                    data_row['original_currency'] = 'EUR'
                    data_row['original_amount'] = row['sale-amount']
                    data_row['user_id'], data_row['placement'] = self.map_placement_and_user(row['sid'])
                    # TODO: not sure when action status sets to closed but it has not happened for
                    # us yet.
                    if dateutil.parser.parse(row['locking-date']) < datetime.datetime.now() and row['action-status'] == 'closed':
                        data_row['status'] = Sale.CONFIRMED
                    else:
                        data_row['status'] = Sale.PENDING
                    data_row['sale_date'] = dateutil.parser.parse(row['event-date'])

                    # If original is not true it must be a correction of some sort
                    data_row['original_commission'] = decimal.Decimal(data_row['original_commission'])
                    data_row['original_amount'] = decimal.Decimal(data_row['original_amount'])
                    if row['original'] != 'true':
                        try:
                            sale = Sale.objects.get(original_sale_id=data_row['original_sale_id'])
                            if sale:
                                data_row['original_commission'] = sale.original_commission + data_row['original_commission']
                                data_row['original_amount'] = sale.original_amount + data_row['original_amount']
                                data_row['adjusted'] = True
                                if data_row['original_commission'] <= decimal.Decimal('0.0'):
                                    data_row['status'] = Sale.DECLINED
                        except Sale.DoesNotExist:
                            logger.error('Correction but no sale in database, should not happen')

                    data_row = self.validate(data_row)
                    if not data_row:
                        continue

                    yield data_row
