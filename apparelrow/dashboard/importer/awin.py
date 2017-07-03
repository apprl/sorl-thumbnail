import hmac
import hashlib
import base64
import datetime
import json
import uuid
import requests
from requests.exceptions import RequestException
import dateutil.parser
import time
import logging

from apparelrow.dashboard.models import Sale
from apparelrow.dashboard.importer.base import BaseImporter

logger = logging.getLogger('affiliate_networks')


class Importer(BaseImporter):

    name = 'Awin'
    oath2 = 'd910c415-9306-444f-9feb-52bdcc4e2b20'


    def map_status(self, status_string):
        if status_string == 'approved':
            return Sale.CONFIRMED
        elif status_string == 'declined':
            return Sale.DECLINED

        return Sale.PENDING


    def get_data(self, start_date, end_date, data=None):
        for start_date, end_date in self.generate_subdates(start_date, end_date, 1):
            start_date_f = start_date.isoformat()
            end_date_f = end_date.isoformat()
            print start_date
            url = 'https://api.awin.com/publishers/115076/transactions/?startDate={}T00%3A00%3A00&endDate={}T00%3A00%3A00&timezone=UTC'.format(
                start_date_f,
                end_date_f
            )

            try:
                response = requests.get(url,
                                        headers={'Authorization': 'Bearer d910c415-9306-444f-9feb-52bdcc4e2b20'})
                print "response from url request: %s" % response
                response.raise_for_status()
                logger.info(
                    "Awin - Request sent successfully to url {} with status code {}".format(url, response.status_code))
            except RequestException as e:
                logger.warning("Awin - Connection error %s" % e)
                return
            report = json.loads(response.content)
            #eport = test_parse() # redo when you get real data from Awin
            for row in report:
                data_row = {}
                data_row['original_sale_id'] = row['id']
                data_row['affiliate'] = self.name
                #_, data_row ['vendor'] = self.map_vendor(row['advertiserId'])
                data_row['original_commission'] = row['commissionAmount']['amount']
                data_row['original_currency'] = row['commissionAmount']['currency']

                data_row['original_amount'] = row['saleAmount']['amount']
                data_row['user_id'] = row['publisherId']
                #data_row ['product_id'] =
                #data_row ['placement'] =
                data_row ['source_link'] = row['publisherUrl']

                data_row['sale_date'] = dateutil.parser.parse(row['transactionDate'])

                status = row['commissionStatus']
                if status == 'deleted':
                    continue
                data_row['status'] = self.map_status(status)

                data_row = self.validate(data_row)
                # print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'

                #for k, v in data_row.items():
                #    print'report row data - {} : {}'.format(k, v)

                if not data_row: # if not true dvs if false
                    continue
                else:
                    yield data_row # yield skapar en iterator som itererar over ett elemnt


def test_parse():
    # TEST METHOD
    # hardcoded json object, since awin do not provide us with data yet 3-07-2017
    request_data = '[{"id": 259630312, "url": "http://www.publisher.com", "advertiserId": 7052,' \
                   ' "publisherId": 189069,  "siteName": "Publisher",  "commissionStatus": "pending",' \
                   '"commissionAmount": {"amount": 5.59,    "currency": "GBP"  },' \
                   '"saleAmount": {"amount": 55.96,"currency": "GBP"  },' \
                   '"clickRefs": {"clickRef": "12345", "clickRef2": "22222",' \
                   ' "clickRef3": "33333","clickRef4": "44444",' \
                   '"clickRef5": "55555", "clickRef6": "66666"},' \
                   '"clickDate": "2017-01-23T12:18:00", "transactionDate": "2017-02-20T22:04:00",  ' \
                   '"validationDate": null, "type": "Commission group transaction",  "declineReason": null,  ' \
                   '"voucherCodeUsed": false, "lapseTime": 2454307, "amended": false,  "amendReason": null, ' \
                   ' "oldSaleAmount": null, "oldCommissionAmount": null,  "clickDevice": "Windows", ' \
                   ' "transactionDevice": "Windows",  "publisherUrl": "http://www.publisher.com/search?query=dvds",  ' \
                   '"advertiserCountry": "GB", "orderRef": "111222333444",' \
                   '"customParameters": [{"key": "1", "value": "555666"}, {"key": "2", "value": "example entry"},' \
                   '{"key": "3", "value": "LLLMMMNNN"}], "transactionParts":' \
                   '[{"commissionGroupId": 12345, "amount": 44.76}, {"commissionGroupId": 654321, "amount": 11.20}],' \
                   '"paidToPublisher": false, "paymentId": 0, "transactionQueryId": 0, "originalSaleAmount": null}]'
    report = json.loads(request_data)

    for r in report:
        print('report row data: %s' % r)
    return report
