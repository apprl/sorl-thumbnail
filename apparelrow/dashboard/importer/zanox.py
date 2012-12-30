import hmac
import hashlib
import base64
import datetime
import uuid
import requests

from dashboard.importer.base import BaseImporter


class GMT(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=0)
    def tzname(self, dt):
        return 'GMT'
    def dst(self, dt):
        return datetime.timedelta(hours=0)


class ZanoxImporter(BaseImporter):

    connect_id = '0FFCC51428993F4F096B'
    secret_key = '68C9E0398Bd44A+1ac9afa55530715/d2b26bB4c'

    def get_nonce(self):
        return uuid.uuid4().hex[:20]

    def get_signature(self, verb, uri):
        timestamp = datetime.datetime.utcnow()
        timestamp = timestamp.replace(tzinfo=GMT())
        timestamp = timestamp.strftime('%a, %d %b %Y %H:%M:%S %Z')
        nonce = self.get_nonce()
        signature = verb + uri + timestamp + nonce

        hmac_signature = hmac.new(self.secret_key, signature, hashlib.sha1)
        hmac_signature = base64.b64encode(hmac_signature.digest())

        return hmac_signature, timestamp, nonce

    def get_data(self, start_date, end_date):
        signature, timestamp, nonce = self.get_signature('GET', '/reports/sales/date/2012-12-17')

        url = 'http://api.zanox.com/json/2011-03-01/reports/sales/date/2012-12-17'
        headers = {'Date': timestamp,
                   'Nonce': nonce,
                   'Authorization': 'ZXWS %s:%s' % (self.connect_id, signature)}
        response = requests.get(url, headers=headers)

        for item in response.json['saleItems']['saleItem']:
            yield item
