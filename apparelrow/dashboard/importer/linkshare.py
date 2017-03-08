import requests
import csv
import decimal
import dateutil.parser
import logging
import datetime
from decimal import Decimal as D
from requests.exceptions import RequestException
from apparelrow.dashboard.models import Sale
from apparelrow.dashboard.importer.base import BaseImporter

logger = logging.getLogger('affiliate_networks')


# I got the Linkshare importer working again. It hadn't been working since 2015.
# They made API changes:
# https://pubhelp.rakutenmarketing.com/hc/en-us/articles/207412163-Changes-to-Reporting-APIs-Effective-February-17-2016
# This is still a work in progress, we need to add unit tests and also import US network so we get Tictail transactions

class Importer(BaseImporter):

    name = 'Linkshare'
    CONFIRM_AFTER_DAYS = 61

    US_NETWORK = 1
    UK_NETWORK = 3

    def get_data(self, start_date, end_date, data=None):
        logger.info("Linkshare - Start importing from Affiliate Network")

        for network in [self.US_NETWORK, self.UK_NETWORK]:
            data = self.make_network_request(network, start_date, end_date)
            if not data:
                continue
            reader = csv.DictReader(data, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                data_row = self.import_row(row)
                data_row = self.validate(data_row)
                if not data_row:
                    continue
                else:
                    yield data_row

    def make_network_request(self, network, start_date, end_date):
        # Make a request to the api to get the report for the subnetwork.
        logger.info("Linkshare - Importing from Network %d" % network)
        try:
            url = self.get_api_url(network, start_date, end_date)
            res = requests.get(url)
            logger.debug("Linkshare - Request sent successfully with status code %s" % res.status_code)
            return res.text.encode('utf-8').splitlines()
        except RequestException as e:
            logger.warning("Linkshare - Connection error %s" % e)

    def get_api_url(self, network, start_date, end_date):
        token = 'ZW5jcnlwdGVkYToyOntzOjU6IlRva2VuIjtzOjY0OiIwODI3MjgzZWY4ODEyNGE2ZWU0ZWYzNmI4OGE1OGRkMDMwMzMyZDBlNmZiYjliMjA3YTI3MDIwNDgxYTM4MTdhIjtzOjg6IlVzZXJUeXBlIjtzOjk6IlB1Ymxpc2hlciI7fQ%3D%3D'
        base_url = 'https://ran-reporting.rakutenmarketing.com/en/reports/apprl-api/filters?network={}&start_date={}&end_date={}&include_summary=N&tz=GMT&date_type=transaction&token={}'
        return base_url.format(
            network,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            token
        )

    def import_row(self, row):
        # Each sale / order in Linkshare is associated with one ore more transactions
        # We assume a transaction never changes but their total will equal the total Sale value
        data_row = {}
        logger.info('Importing transaction %s, order: %s' % (row['Transaction ID'], row['Order ID']))
        try:
            previous_sale = Sale.objects.get(original_sale_id=row['Order ID'])
            data_row['log_info'] = previous_sale.log_info
        except Sale.DoesNotExist:
            data_row['log_info'] = {}

        self.extract_sale_properties(data_row, row)
        self.add_transaction_to_log(data_row, row)
        self.update_total_from_log(data_row)

        self.set_status(data_row)
        return data_row

    def extract_sale_properties(self, data_row, row):
        data_row['original_sale_id'] = row['Order ID']
        data_row['affiliate'] = self.name
        _, data_row['vendor'] = self.map_vendor(row['Advertiser Name'])
        data_row['original_commission'] = D(row['Total Commission'].replace(',', ''))
        data_row['original_amount'] = D(row['Sales'].replace(',', ''))
        data_row['original_currency'] = 'GBP' if not 'Currency' in row else row['Currency']
        data_row['user_id'], data_row['product_id'], data_row['placement'], data_row['source_link'] = self.map_placement_and_user(row['Member ID (U1)'])
        data_row['sale_date'] = dateutil.parser.parse('%s %s' % (row['Transaction Date'], row['Transaction Time']))
        data_row['adjusted_date'] = self.parse_to_utc('%s %s' % (row['Process Date'], row['Process Time'])).replace(tzinfo=None)

    def add_transaction_to_log(self, data_row, row):
        data_row['log_info'][row['Transaction ID']] = {
            'original_commission': data_row['original_commission'],
            'original_amount': data_row['original_amount'],
            'original_currency': data_row['original_currency']
        }

    def update_total_from_log(self, data_row):
        data_row['original_amount'] = sum(D(l['original_amount']) for l in data_row['log_info'].values())
        data_row['original_commission'] = sum(D(l['original_commission']) for l in data_row['log_info'].values())

    def set_status(self, data_row):
        data_row['status'] = Sale.PENDING
        # Confirm sale when enough time has passed
        # TODO: Isn't there a better way to do this?
        if data_row['sale_date'] < datetime.datetime.now() - datetime.timedelta(days=self.CONFIRM_AFTER_DAYS):
            data_row['status'] = Sale.CONFIRMED
        if data_row['original_amount'] <= decimal.Decimal('0.0'):
            data_row['status'] = Sale.DECLINED
