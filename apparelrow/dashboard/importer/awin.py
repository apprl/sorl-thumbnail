import json
import logging
import time

import dateutil.parser
import requests
from requests.exceptions import RequestException

from apparelrow.dashboard.importer.base import BaseImporter
from apparelrow.dashboard.models import Sale
from django.db.models.loading import get_model

logger = logging.getLogger('affiliate_networks')


class Importer(BaseImporter):
    '''
    The API (Publisher API) is available via https://api.awin.com. It uses REST as a standard
    oauth2 for authentication and returns JSON as the default response data format.
    Awin have a throttling in place that limits the number of API requests to 100 API calls per minute per user
    Awin API supports only 31 days
    '''
    name = 'Awin'
    OATH2 = 'd910c415-9306-444f-9feb-52bdcc4e2b20'

    def get_data(self, start_date, end_date, data=None):

        logger.info("Awin - Start importing from Affiliate Network")
        for start_date, end_date in self.generate_subdates(start_date, end_date, 1):

            transaction_url = self.get_transaction_api_url(start_date, end_date)
            transaction_response = self.make_api_request(transaction_url)
            report = json.loads(transaction_response)

            for row in report:
                data_row = self.import_row(row, start_date, end_date)
                data_row = self.validate(data_row)
                if not data_row:
                    continue
                else:
                    yield data_row
            time.sleep(0.5)  # be nice to their servers

    def get_transaction_api_url(self, start_date, end_date):
        url = 'https://api.awin.com/publishers/115076/transactions/?startDate={}T00%3A00%3A00&' \
              'endDate={}T23%3A59%3A59&timezone=UTC'.format(
            start_date,
            end_date
        )
        return url

    def make_api_request(self, url):
        try:
            response = requests.get(url,
                                    headers={'Authorization': 'Bearer ' + self.OATH2})
            print "response from url request: %s" % response
            response.raise_for_status()
            logger.info(
                "Awin - Request sent successfully to url {} with status code {}".format(url, response.status_code))
        except RequestException as e:
            logger.warning("Awin - Connection error %s" % e)
            return

        return response.content

    def import_row(self, row, start_date, end_date):
        data_row = {}
        data_row['original_sale_id'] = row['id']
        data_row['affiliate'] = self.name
        data_row['original_commission'] = row['commissionAmount']['amount']
        data_row['original_currency'] = row['commissionAmount']['currency']
        data_row['original_amount'] = row['saleAmount']['amount']
        data_row['sale_date'] = dateutil.parser.parse(row['transactionDate'])

        sid = ''
        if row['clickRefs']:
            if 'clickRef' in row['clickRefs']:
                sid = row['clickRefs']['clickRef']
            elif 'clickRef2' in row['clickRefs']:
                sid = row['clickRefs']['clickRef2']

        data_row['user_id'], data_row['product_id'], data_row['placement'], data_row[
            'source_link'] = self.map_placement_and_user(sid)
        status = row['commissionStatus']
        data_row['status'] = self.map_status(status)

        region = row['advertiserCountry']

        data_row['vendor'] = self.get_advertiser_name(region, start_date, end_date, row['advertiserId'])

        return data_row

    def map_status(self, status_string):
        if status_string == 'approved':
            return Sale.CONFIRMED
        elif status_string == 'declined':
            return Sale.DECLINED
        elif status_string == 'pending':
            return Sale.PENDING

    def get_advertiser_api_url(self, start_date, end_date, region):
        url = 'https://api.awin.com/publishers/115076/reports/advertiser?startDate={}&endDate={}&region={}&timezone=UTC' \
            .format(
            start_date,
            end_date,
            region
        )
        return url

    def get_advertiser_name(self, region, start_date, end_date, advertiser_id):
        '''
        Awins' Transactions API provides only an advertiser_id. To retrieve the
        advertiser_name, it's extracted from Aggregated by Advertiser API which is another
        api provided by Awin.
        :param advertiser_id: retrieved from Transactions API
        :return: returns advertiser name if found otherwise None
        '''
        url = self.get_advertiser_api_url(start_date, end_date, region)
        advertiser_report = json.loads(self.make_api_request(url))
        advertiser_name = None
        for row in advertiser_report:
            if row['advertiserId'] == advertiser_id:
                _, advertiser_name = self.map_vendor(row['advertiserName'])
                return advertiser_name

        if advertiser_name == None:
            logger.warning("Vendor %s does not exist." % advertiser_name)
            return None
