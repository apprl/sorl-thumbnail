from suds.client import Client
from suds.xsd.doctor import ImportDoctor, Import
import dateutil.parser
import logging
import requests
from requests.exceptions import RequestException

from apparelrow.dashboard.models import Sale
from apparelrow.dashboard.importer.base import BaseImporter

logger = logging.getLogger('affiliate_networks')


class Importer(BaseImporter):
    """
    How to handle corrections/adjustments? No information available...
    """
    name = 'Affiliate Window'
    auth_id = 115076
    auth_password = 'ab70c6d0a3a49446ac6d51428cf6c5bb5cd7fed52b3e108a'

    def map_status(self, status_string):
        """
        Available statues: confirmed, validation, declined
        """
        if status_string == 'confirmed':
            return Sale.CONFIRMED
        elif status_string == 'declined':
            return Sale.DECLINED

        return Sale.PENDING

    def get_data(self, start_date, end_date, data=None):
        logger.info("AffiliateWindow - Start importing from Affiliate Network")
        url = 'http://api.affiliatewindow.com/v4/AffiliateService?wsdl'
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
        d = ImportDoctor(imp)
        client = Client(url, doctor=d)

        auth = client.factory.create('UserAuthentication')
        auth.iId = self.auth_id
        auth.sPassword = self.auth_password
        auth.sType = 'affiliate'

        try:
            for start_date, end_date in self.generate_subdates(start_date, end_date, 30):
                client.set_options(soapheaders=auth)
                response = client.service.getTransactionList(sDateType='transaction',
                                                             dStartDate=start_date.strftime('%Y-%m-%dT00:00:00'),
                                                             dEndDate=end_date.strftime('%Y-%m-%dT23:59:59'))
                logger.debug("AffiliateWindow - Request sent successfully")

                response_count = response.getTransactionListCountReturn
                if response_count.iRowsReturned > 0:
                    for row in response.getTransactionListReturn.Transaction:
                        data_row = {}
                        merchants = client.factory.create('ArrayOfMerchant')
                        merchants.item = [row.iMerchantId[0]]
                        merchant_response = client.service.getMerchant(aMerchantIds=merchants)
                        data_row['original_sale_id'] = row.iId[0]
                        data_row['affiliate'] = self.name
                        _, data_row['vendor'] = self.map_vendor(merchant_response.Merchant[0].sName[0])
                        data_row['original_commission'] = row.mCommissionAmount[0].dAmount[0]
                        data_row['original_currency'] = row.mCommissionAmount[0].sCurrency[0]
                        data_row['original_amount'] = row.mSaleAmount[0].dAmount[0]
                        data_row['user_id'], data_row['product_id'], data_row['placement'] = self.map_placement_and_user(row.sClickref[0])
                        data_row['status'] = self.map_status(row.sStatus[0])
                        data_row['sale_date'] = dateutil.parser.parse(row.dTransactionDate[0])

                        data_row = self.validate(data_row)
                        if not data_row:
                            continue

                        yield data_row
        except RequestException as e:
            logger.warning("AffiliateWindow - Connection error %s"%e)
