import requests
import csv
import decimal
import dateutil.parser
import logging
import datetime

from apparelrow.dashboard.models import Sale
from apparelrow.dashboard.importer.base import BaseImporter

logger = logging.getLogger('affiliate_networks')


class Importer(BaseImporter):

    name = 'Linkshare'
    token = '0827283ef88124a6ee4ef36b88a58dd030332d0e6fbb9b207a27020481a3817a'
    network_id = 3

    def get_data(self, start_date, end_date):
        logger.info("Linkshare - Start importing from Affiliate Network")
        url = 'https://reportws.linksynergy.com/downloadreport.php?bdate=%s&edate=%s&token=%s&nid=%s&reportid=12' % (start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'), self.token, self.network_id)

        try:
            response = requests.get(url)
            logger.debug("Linkshare - Request sent successfully with status code %s"%(response.status_code))
            data = response.text.encode('utf-8').splitlines()
            reader = csv.DictReader(data, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                data_row = {}
                data_row['original_sale_id'] = '%s-%s' % (row['Order ID'], row['SKU Number'])
                data_row['affiliate'] = self.name
                _, data_row['vendor'] = self.map_vendor(row['Merchant Name'])
                data_row['original_commission'] = row['Commissions($)'].replace(',', '')
                # TODO: same commission and amount for both USD and GBP from two
                # diffrent reports, set GBP for now, can change when we know more.
                data_row['original_currency'] = 'GBP'
                data_row['original_amount'] = row['Sales($)'].replace(',', '')
                data_row['user_id'], data_row['product_id'], data_row['placement'] = self.map_placement_and_user(row['Member ID'])
                data_row['sale_date'] = dateutil.parser.parse('%s %s' % (row['Transaction Date'], row['Transaction Time']))
                # Confirm transaction after 100 days
                # TODO: verify this
                data_row['status'] = Sale.PENDING
                if data_row['sale_date'] < datetime.datetime.now() - datetime.timedelta(days=61):
                    data_row['status'] = Sale.CONFIRMED


                data_row['adjusted_date'] = self.parse_to_utc('%s %s' % (row['Process Date'], row['Process Time'])).replace(tzinfo=None)

                # If commission is negative it must be a correction
                data_row['original_commission'] = decimal.Decimal(data_row['original_commission'])
                data_row['original_amount'] = decimal.Decimal(data_row['original_amount'])
                if data_row['original_commission'] < decimal.Decimal('0.0'):
                    try:
                        sale = Sale.objects.get(original_sale_id=data_row['original_sale_id'])
                        if sale:
                            if not sale.adjusted_date or (sale.adjusted_date and sale.adjusted_date < data_row['adjusted_date']):
                                data_row['original_commission'] = sale.original_commission + data_row['original_commission']
                                data_row['original_amount'] = sale.original_amount + data_row['original_amount']
                            else:
                                continue

                            data_row['adjusted'] = True
                            if data_row['original_commission'] <= decimal.Decimal('0.0'):
                                data_row['status'] = Sale.DECLINED
                    except Sale.DoesNotExist:
                        logger.error('Linkshare - Correction but no sale in database')

                data_row = self.validate(data_row)
                if not data_row:
                    continue

                yield data_row
        except requests.exceptions.RequestException as e:
            logger.warning("Linkshare - Connection error %s"%e)
