import json
import logging
import time

import dateutil.parser
import requests
from requests.exceptions import RequestException

from apparelrow.dashboard.importer.base import BaseImporter
from apparelrow.dashboard.models import Sale

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

    def map_status(self, status_string):
        if status_string == 'approved':
            return Sale.CONFIRMED
        elif status_string == 'declined':
            return Sale.DECLINED
        return Sale.PENDING

    def get_data(self, start_date, end_date, data=None):
        logger.info("Awin - Start importing from Affiliate Network")
        for start_date, end_date in self.generate_subdates(start_date, end_date, 1):
            url = self.get_api_url(start_date, end_date)
            response = self.make_api_request(url)
            report = response.content
            data_row = self.import_row(report)
            data_row = self.validate(data_row)
            if not data_row:
                continue
            else:
                yield data_row
            time.sleep(0.5)  # be nice to their servers

    def import_row(self, report):
        report = json.loads(report)
        data_row = {}
        for row in report:
            data_row['original_sale_id'] = row['id']
            data_row['affiliate'] = self.name
            data_row['original_commission'] = row['commissionAmount']['amount']
            data_row['original_currency'] = row['commissionAmount']['currency']
            data_row['original_amount'] = row['saleAmount']['amount']
            data_row['user_id'] = row['publisherId']
            data_row['source_link'] = row['publisherUrl']

            data_row['sale_date'] = dateutil.parser.parse(row['transactionDate'])
            status = row['commissionStatus']
            if status == 'deleted':
                continue
            data_row['status'] = self.map_status(status)
        return data_row

    def get_api_url(self, start_date, end_date):

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

        return response
