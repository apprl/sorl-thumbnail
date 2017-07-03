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


class GMT(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=0)
    def tzname(self, dt):
        return 'GMT'
    def dst(self, dt):
        return datetime.timedelta(hours=0)


class Importer(BaseImporter):
    """
    No product information available in sale reports from zanox.

    TODO: how to handle corrections/adjustments for zanox?
    """
    name = 'Awin'
    oath2 = 'd910c415-9306-444f-9feb-52bdcc4e2b20'



    def get_signature(self, verb, uri):
        timestamp = datetime.datetime.utcnow()
        timestamp = timestamp.replace(tzinfo=GMT())
        timestamp = timestamp.strftime('%a, %d %b %Y %H:%M:%S %Z')
        nonce = self.get_nonce()
        signature = verb + uri + timestamp + nonce

        hmac_signature = hmac.new(self.secret_key, signature, hashlib.sha1)
        hmac_signature = base64.b64encode(hmac_signature.digest())

        return hmac_signature, timestamp, nonce

    def map_status(self, status_string):
        """
        Open
        Leads which have not yet been approved by the advertiser

        Approved
        Leads which have been approved by the advertiser

        Confirmed
        Leads which have been approved by the advertiser and confirmed by zanox.
        Leads are only confirmed if the advertiser's account balance is positive.

        Rejected
        Leads which have been rejected by the advertiser.

        Source: http://www.zanox.com/export/sites/default/en/_downloads/help/zanox_UserGuide_Advertiser_EN.pdf
        """
        if status_string == 'approved':
            return Sale.CONFIRMED
        elif status_string == 'declined':
            return Sale.DECLINED

        return Sale.PENDING

    def get_headers(self, base_url):
        signature, timestamp, nonce = self.get_signature('GET', base_url)
        return {
            'Date': timestamp,
            'Nonce': nonce,
            'Authorization': 'ZXWS %s:%s' % (self.connect_id, signature)
        }

    def get_data(self, start_date, end_date, data=None):
        request_data = '[{  "id": 259630312,  "url": "http://www.publisher.com",  "advertiserId": 7052,  "publisherId": 189069,  "siteName": "Publisher",  "commissionStatus": "pending",  "commissionAmount": {    "amount": 5.59,    "currency": "GBP"  },  "saleAmount": {    "amount": 55.96,    "currency": "GBP"  },  "clickRefs": {    "clickRef": "12345",    "clickRef2": "22222",    "clickRef3": "33333",    "clickRef4": "44444",    "clickRef5": "55555",    "clickRef6": "66666"  },  "clickDate": "2017-01-23T12:18:00",  "transactionDate": "2017-02-20T22:04:00",  "validationDate": null,  "type": "Commission group transaction",  "declineReason": null,  "voucherCodeUsed": false,  "lapseTime": 2454307,  "amended": false,  "amendReason": null,  "oldSaleAmount": null,  "oldCommissionAmount": null,  "clickDevice": "Windows",  "transactionDevice": "Windows",  "publisherUrl": "http://www.publisher.com/search?query=dvds",  "advertiserCountry": "GB",  "orderRef": "111222333444",  "customParameters": [{      "key": "1",      "value": "555666"    },    {      "key": "2",      "value": "example entry"    },    {      "key": "3",      "value": "LLLMMMNNN"    }  ],  "transactionParts": [{      "commissionGroupId": 12345,      "amount": 44.76    },    {      "commissionGroupId": 654321,      "amount": 11.20    }  ],  "paidToPublisher": false,  "paymentId": 0,  "transactionQueryId": 0,  "originalSaleAmount": null}]'
        report = json.loads(request_data)
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

            if not data_row: # if not true dvs if false
                continue
            else:
                yield data_row # yield skapar en iterator som itererar över ett elemnt



        def test_parse():
            # hardcoded json object, since awin do not provide us with data yet 3-07-2017

            request_data = '{ "advertiserId": 1001, "advertiserName": "Example Advertiser", "publisherId": 45628, ' \
                           '"publisherName": "Example Publisher", "region": "GB", "currency": "GBP", "impressions": 0,\
                           "clicks": 0, "pendingNo": 0, "pendingValue": 0, "pendingComm": 0, "confirmedNo": 0, "confirmedValue": 0, ' \
                           '"confirmedComm": 0, "bonusNo": 1, "bonusValue": 0, "bonusComm": 2500, "totalNo": 1,\
                           "totalValue": 0, "totalComm": 2500, "declinedNo": 0, "declinedValue": 0, "declinedComm": 0	}'
            # loads is the same as parse in javascript
            report = json.loads(request_data)

            for r in report:
                print('report row data: %s' % r)



test_parse()