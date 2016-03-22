import requests
import csv
import decimal
import dateutil.parser
import logging
import datetime
from requests.exceptions import RequestException
from apparelrow.dashboard.models import Sale
from apparelrow.dashboard.importer.base import BaseImporter

logger = logging.getLogger('affiliate_networks')


class Importer(BaseImporter):

    name = 'Linkshare'
    token = '0827283ef88124a6ee4ef36b88a58dd030332d0e6fbb9b207a27020481a3817a'
    network_id = 3

    def get_data(self, start_date, end_date, data=None):
        logger.info("Linkshare - Start importing from Affiliate Network")
        url = 'https://reportws.linksynergy.com/downloadreport.php?bdate=%s&edate=%s&token=%s&nid=%s&reportid=12' % (start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'), self.token, self.network_id)
        try:
            if not data:
                response = requests.get(url)
                logger.debug("Linkshare - Request sent successfully with status code %s"%(response.status_code))
                data = response.text.encode('utf-8').splitlines()
            reader = csv.DictReader(data, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                old_sale_id = '%s-%s' % (row['Order ID'], row['SKU Number'])

                # If it is not an old format sale record proceed
                if not Sale.objects.filter(original_sale_id=old_sale_id).exists():
                    data_row = {}

                    # Now sale ID is just based on Order ID, to handle the multiple products on the sale
                    # Common attributes
                    data_row['original_sale_id'] = '%s' % (row['Order ID'])

                    #Collect the data from the row
                    data_row['affiliate'] = self.name
                    _, data_row['vendor'] = self.map_vendor(row['Merchant Name'])
                    data_row['original_commission'] = row['Commissions($)'].replace(',', '')
                    # TODO: same commission and amount for both USD and GBP from two
                    # diffrent reports, set GBP for now, can change when we know more.
                    data_row['original_currency'] = 'GBP' if not 'Currency' in row else row['Currency']
                    data_row['original_amount'] = row['Sales($)'].replace(',', '')
                    data_row['user_id'], data_row['product_id'], data_row['placement'], data_row['source_link'] = self.map_placement_and_user(row['Member ID'])
                    data_row['sale_date'] = dateutil.parser.parse('%s %s' % (row['Transaction Date'], row['Transaction Time']))

                    # Confirm transaction after 100 days
                    # TODO: verify this
                    data_row['status'] = Sale.PENDING
                    if data_row['sale_date'] < datetime.datetime.now() - datetime.timedelta(days=61):
                        data_row['status'] = Sale.CONFIRMED

                    data_row['adjusted_date'] = self.parse_to_utc('%s %s' % (row['Process Date'], row['Process Time'])).replace(tzinfo=None)

                    data_row['original_commission'] = decimal.Decimal(data_row['original_commission'])
                    data_row['original_commission'] = decimal.Decimal("%.2f"%(round(data_row['original_commission'],2)))
                    data_row['original_amount'] = decimal.Decimal(data_row['original_amount'])
                    # Check if sale already exists
                    if Sale.objects.filter(original_sale_id=data_row['original_sale_id']).exists():
                        try:
                            commission = data_row['original_commission']
                            amount = data_row['original_amount']

                            sale = Sale.objects.get(original_sale_id=data_row['original_sale_id'])

                            # Get information from the existent sale
                            data_row['original_commission'] = sale.original_commission
                            data_row['original_amount'] = sale.original_amount
                            data_row['log_info'] = sale.log_info if sale.log_info else {}

                            if not row['SKU Number'] in data_row['log_info']:
                                data_row['original_commission'] += commission
                                data_row['original_amount'] += amount
                                data_row['log_info'][row['SKU Number']]= []
                                if data_row['original_amount'] >= 0:
                                    data_row['log_info'][row['SKU Number']].append(sale.PRODUCT_ADDED)
                                else:
                                    data_row['log_info'][row['SKU Number']].append(sale.PRODUCT_DECLINED)
                            else:
                                if amount >= 0 and not sale.PRODUCT_ADDED in data_row['log_info'][row['SKU Number']]:
                                    data_row['original_commission'] += commission
                                    data_row['original_amount'] += amount
                                    data_row['log_info'][row['SKU Number']].append(sale.PRODUCT_ADDED)
                                elif amount < 0 and not sale.PRODUCT_DECLINED in data_row['log_info'][row['SKU Number']]:
                                    data_row['original_commission'] += commission
                                    data_row['original_amount'] += amount
                                    data_row['log_info'][row['SKU Number']].append(sale.PRODUCT_DECLINED)

                        except Sale.MultipleObjectsReturned:
                            logger.warning("Multiple objects returned for sale %s"%(data_row['original_sale_id']))
                    else:
                        data_row['log_info'] = {}
                        data_row['log_info'][row['SKU Number']]= []

                        if data_row['original_commission'] < decimal.Decimal('0.0'):
                            data_row['log_info'][row['SKU Number']].append(Sale.PRODUCT_DECLINED)
                        else:
                            data_row['log_info'][row['SKU Number']].append(Sale.PRODUCT_ADDED)
                    if data_row['original_amount'] <= decimal.Decimal('0.0'):
                        data_row['status'] = Sale.DECLINED
                    data_row = self.validate(data_row)
                    if not data_row:
                        continue
                    yield data_row
        except RequestException as e:
            logger.warning("Linkshare - Connection error %s"%e)
