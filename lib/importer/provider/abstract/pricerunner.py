from importer.provider import Provider as ProviderBase
from importer.mapper import DataMapper

import libxml2, re
from xml.sax.saxutils import unescape

class PriceRunnerProvider(ProviderBase):
    """
    Imports product feed from Acne Jeans
    """
    
    def __init__(self, **kwargs):
        # Set configurations here
        ProviderBase.__init__(self, **kwargs)
        
        self.extension = 'xml'
    
    def process(self):
        if not self.file:
            raise Exception('No source file available')
        
        if not self.mapper:
            raise Exception('No mapper class specified in PriceRunner subclass')
        
        doc = libxml2.parseFile(self.file) #, 'utf8', libxml2.XML_PARSE_NOENT)
        context = doc.xpathNewContext()
        
        # Global variables
        vendor_name = context.xpathEval('/Products/@company')
        if vendor_name:
            vendor_name = vendor_name[0].content.capitalize()
        
        for product in context.xpathEval('//Product'):
            # FIXME: The unescape routine only handles <, > and &. This needs
            # to be fixed.

            row = dict([(e.name.lower(), unescape(e.getContent())) for e in product.xpathEval('./*')])
            row['categories'] = [unescape(c.getContent()) for c in product.xpathEval('./Categories/*')]
            row['vendorname'] = vendor_name
            mapper = self.mapper(self, row)
            mapper.translate()
        
        context.xpathFreeContext()
        doc.freeDoc()


class PriceRunnerMapper(DataMapper):
    def set_manufacturer_name(self, value):
        return self.data.get('brand')
    
    def set_product_image_url(self, value):
        return self.data.get('imageurl')
        
    def set_product_name(self, value):
        return self.data.get('name')
    
    def set_vendor_option_buy_url(self):
        return self.data.get('producturl')
    
    def set_vendor_option_currency(self):        
        return self.data.get('currency')
        
    def set_vendor_option_price(self):
        return self.data.get('priceincvat')

    def set_vendor_name(self, value):
        return self.data.get('vendorname')
