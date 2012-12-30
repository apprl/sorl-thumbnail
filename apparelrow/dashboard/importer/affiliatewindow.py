from suds.client import Client
from suds.xsd.doctor import ImportDoctor, Import
import hashlib

#from dashboard.importer.base import BaseImporter

import logging
logging.basicConfig(level=logging.DEBUG)

#class AffiliateWindowImporter(BaseImporter):
class AffiliateWindowImporter:

    def get_data(self):
        url = 'http://api.affiliatewindow.com/v4/AffiliateService?wsdl'
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
        d = ImportDoctor(imp)
        client = Client(url, doctor=d)

        auth = client.factory.create('UserAuthentication')
        auth.iId = 115076
        auth.sPassword = 'apprlwindow2010'
        auth.sType = 'affiliate'

        #from suds.sax.element import Element
        #ssnns = ('ns1', 'http://api.affiliatewindow.com/')
        #auth = Element('UserAuthentication', ns=ssnns)
        #auth.set('SOAP-ENV:mustUnderstand', '1')
        #auth.set('SOAP-ENV:actor', 'http://api.affiliatewindow.com')
        #user_id = Element('iId', ns=ssnns).setText(115076)
        #password = Element('sPassword', ns=ssnns).setText(hashlib.md5('apprlwindow2010').hexdigest())
        #user_type = Element('sType', ns=ssnns).setText('affiliate')
        #auth.append(user_id)
        #auth.append(password)
        #auth.append(user_type)

        client.set_options(soapheaders=auth)
        print client.service.getTransactionList()

print AffiliateWindowImporter().get_data()
