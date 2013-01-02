from suds.client import Client
from suds.xsd.doctor import ImportDoctor, Import
import hashlib
import math
import datetime
import dateutil.parser

from dashboard.importer.base import BaseImporter

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
        # TODO: paid field should be used to elevate status above confirmed
        if status_string == 'confirmed':
            return 'C'
        elif status_string == 'declined':
            return 'D'

        return 'P'

    def get_data(self, start_date, end_date):
        url = 'http://api.affiliatewindow.com/v4/AffiliateService?wsdl'
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
        d = ImportDoctor(imp)
        client = Client(url, doctor=d)

        auth = client.factory.create('UserAuthentication')
        auth.iId = self.auth_id
        auth.sPassword = self.auth_password
        auth.sType = 'affiliate'

        interval_days = (end_date - start_date).days + 1
        periods = int(math.ceil(interval_days / 30))

        for period in range(periods):
            end_date = start_date + datetime.timedelta(days=30)

            client.set_options(soapheaders=auth)
            response = client.service.getTransactionList(sDateType='transaction',
                                                         dStartDate=start_date.strftime('%Y-%m-%dT00:00:00'),
                                                         dEndDate=end_date.strftime('%Y-%m-%dT23:59:59'))

            response_count = response.getTransactionListCountReturn
            if response_count.iRowsReturned > 0:
                data_row = {}
                for row in response.getTransactionListReturn.Transaction:
                    merchants = client.factory.create('ArrayOfMerchant')
                    merchants.item = [row.iMerchantId[0]]
                    merchant_response = client.service.getMerchant(aMerchantIds=merchants)
                    data_row['original_sale_id'] = row.iId[0]
                    data_row['affiliate'] = self.name
                    _, data_row['vendor'] = self.map_vendor(merchant_response.Merchant[0].sName[0])
                    data_row['commission'] = row.mCommissionAmount[0].dAmount[0]
                    data_row['currency'] = row.mCommissionAmount[0].sCurrency[0]
                    data_row['amount'] = row.mSaleAmount[0].dAmount[0]
                    data_row['user_id'], data_row['placement'] = self.map_placement_and_user(row.sClickref[0])
                    data_row['status'] = self.map_status(row.sStatus[0])
                    data_row['sale_date'] = dateutil.parser.parse(row.dTransactionDate[0])

                    yield data_row

            start_date = end_date
