import requests
import datetime
import xmltodict
import math
import decimal
import dateutil.parser

from django.db.models.loading import get_model

from dashboard.importer.base import BaseImporter

class Importer(BaseImporter):

    name = 'CJ'
    api_key = '008765b01c28856695bf9e6d1cf5a964c828bd64e087f52702d89cf427ba83cdeba00854d1b2ed9151887662aad9d9871c15a21e7bc0d97214d51648835c533a33/7ff6c059ec861fad39dbce3e0783a02778317f8ca19235db7fc3df11493ad6bb1189e6776f22d162c90449ae44dd21331c04606bf8d3aee2e4645f7de06b6571'

    def get_data(self, start_date, end_date):
        interval_days = (end_date - start_date).days + 1
        periods = int(math.ceil(interval_days / 30))

        print start_date, end_date
        for period in range(periods):
            end_date = start_date + datetime.timedelta(days=30)
            print start_date, end_date, period

            headers = {'authorization': self.api_key}
            url = 'https://commission-detail.api.cj.com/v3/commissions?date-type=posting&start-date=%s&end-date=%s' % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            response = requests.get(url, headers=headers)
            data = xmltodict.parse(response.text)
            if int(data['cj-api']['commissions']['@total-matched']) > 0:
                data_row = {}
                for row in data['cj-api']['commissions']['commission']:
                    data_row['original_sale_id'] = row['original-action-id']
                    data_row['affiliate'] = self.name
                    _, data_row['vendor'] = self.map_vendor(row['advertiser-name'])
                    data_row['commission'] = row['commission-amount']
                    data_row['currency'] = 'EUR'
                    data_row['amount'] = row['sale-amount']
                    data_row['user_id'], data_row['placement'] = self.map_placement_and_user(row['sid'])
                    if dateutil.parser.parse(row['locking-date']) < datetime.datetime.now() and row['action-status'] == 'closed':
                        data_row['status'] = 'C'
                    else:
                        data_row['status'] = 'P'
                    data_row['sale_date'] = dateutil.parser.parse(row['event-date'])

                    # If original is not true it must be a correction of some sort
                    data_row['commission'] = decimal.Decimal(data_row['commission'])
                    data_row['amount'] = decimal.Decimal(data_row['amount'])
                    if row['original'] != 'true':
                        try:
                            sale = get_model('dashboard', 'Sale').objects.get(original_sale_id=data_row['original_sale_id'])
                            if sale:
                                data_row['commission'] = sale.commission + data_row['commission']
                                data_row['amount'] = sale.amount + data_row['amount']
                                if data_row['commission'] <= decimal.Decimal('0.0'):
                                    data_row['status'] = 'D'
                        except get_model('dashboard', 'Sale').DoesNotExist:
                            logger.error('Correction but no sale in database')

                    yield data_row

            start_date = end_date
