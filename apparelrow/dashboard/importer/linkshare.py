import requests
import csv
import decimal
import dateutil.parser

from django.db.models.loading import get_model

from dashboard.importer.base import BaseImporter

class Importer(BaseImporter):

    name = 'Linkshare'
    token = '0827283ef88124a6ee4ef36b88a58dd030332d0e6fbb9b207a27020481a3817a'
    network_id = 3

    def get_data(self, start_date, end_date):
        url = 'https://reportws.linksynergy.com/downloadreport.php?bdate=%s&edate=%s&token=%s&nid=%s&reportid=12' % (start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'), self.token, self.network_id)

        response = requests.get(url)
        data = response.text.encode('utf-8').splitlines()
        reader = csv.DictReader(data, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        data_row = {}
        for row in reader:
            data_row['original_sale_id'] = '%s-%s' % (row['Order ID'], row['SKU Number'])
            data_row['affiliate'] = self.name
            _, data_row['vendor'] = self.map_vendor(row['Merchant Name'])
            data_row['commission'] = row['Commissions($)'].replace(',', '')
            # TODO: same commission and amount for both USD and GBP from two
            # diffrent reports, set GBP for now, can change when we know more.
            data_row['currency'] = 'GBP'
            data_row['amount'] = row['Sales($)'].replace(',', '')
            data_row['user_id'], data_row['placement'] = self.map_placement_and_user(row['Member ID'])
            data_row['sale_date'] = dateutil.parser.parse('%s %s' % (row['Transaction Date'], row['Transaction Time']))

            try:
                sale = get_model('dashboard', 'Sale').objects.get(original_sale_id=data_row['original_sale_id'])
                if sale and decimal.Decimal(data_row['commission']) + sale.commission == decimal.Decimal(0.0):
                    data_row['status'] = 'D'
            except get_model('dashboard', 'Sale').DoesNotExist:
                pass

            import pprint
            pprint.pprint(row)

            yield data_row
