import hmac
import hashlib
import base64
import datetime
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
    name = 'Zanox'
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
        if status_string == 'confirmed':
            return Sale.CONFIRMED
        elif status_string == 'rejected':
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
        logger.info("Zanox - Start importing from Affiliate Network")
        for start_date, end_date in self.generate_subdates(start_date, end_date, 1):

            page = 0
            items_per_page = 50  # 50 is max for zonox api
            has_more_pages = True

            while has_more_pages:
                base_url = '/reports/sales/date/' + end_date.strftime('%Y-%m-%d')
                url = 'http://api.zanox.com/json/2011-03-01{}?items={}&page={}'.format(
                    base_url,
                    items_per_page,
                    page
                )
                #f = open('debug/%s_%s.json' % (end_date, page), 'w')
                try:
                    response = requests.get(url, headers=self.get_headers(base_url))
                    response.raise_for_status()
                    logger.info("Zanox - Request sent successfully to url {} with status code {}".format(url, response.status_code))
                except RequestException as e:
                    logger.warning("Zanox - Connection error %s" % e)
                    return
                #f.write(response.content)

                data = response.json()
                if 'saleItems' in data:
                    for row in data['saleItems']['saleItem']:
                        data_row = {}
                        data_row['original_sale_id'] = row['@id']
                        data_row['affiliate'] = self.name
                        _, data_row ['vendor'] = self.map_vendor(row['program']['$'])
                        data_row['original_commission'] = row['commission']
                        data_row['original_currency'] = row['currency']
                        data_row['original_amount'] = row['amount']
                        if 'gpps' in row:
                            sid = row['gpps']['gpp']['$']
                        else:
                            sid = ''
                        data_row['user_id'], data_row ['product_id'], data_row ['placement'], data_row ['source_link'] = self.map_placement_and_user(sid)
                        data_row['sale_date'] = dateutil.parser.parse(row['trackingDate'])
                        data_row['status'] = self.map_status(row['reviewState'])

                        data_row = self.validate(data_row)
                        if not data_row:
                            continue
                        else:
                            yield data_row

                time.sleep(0.5)  # be nice to their servers

                # should we keep going?
                has_more_pages = (data.get('total', 0) > (page+1)*items_per_page)
                if has_more_pages:
                    page = page + 1
