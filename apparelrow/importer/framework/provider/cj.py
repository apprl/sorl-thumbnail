import re

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper

# Columns:
#    ADVERTISERCATEGORY
#    ARTIST
#    AUTHOR
#    BUYURL
#    CATALOGNAME
#    CONDITION
#    CURRENCY
#    DESCRIPTION
#    ENDDATE
#    FORMAT
#    FROMPRICE
#    GIFT
#    IMAGEURL
#    IMPRESSIONURL
#    INSTOCK
#    ISBN
#    KEYWORDS
#    LABEL
#    LASTUPDATED
#    MANUFACTURER
#    MANUFACTURERID
#    NAME
#    OFFLINE
#    ONLINE
#    PRICE
#    PROGRAMNAME
#    PROGRAMURL
#    PROMOTIONALTEXT
#    PUBLISHER
#    RETAILPRICE
#    SALEPRICE
#    SKU
#    SPECIAL
#    STANDARDSHIPPINGCOST
#    STARTDATE
#    THIRDPARTYCATEGORY
#    THIRDPARTYID
#    TITLE
#    UPC
#    WARRANTY
#
# Note: Column names are lower cased
#   



class CJMapper(DataMapper):
    re_cdata = re.compile(r'<!\[CDATA\[(.+?)\]\]>')
    re_quote = re.compile(r'^"*|(?<!\d)"|"*$')          # The middle segment preserves inches
    re_yes   = re.compile(r'^yes$', re.I)
    re_price = re.compile(r'[^\d\.]')
    
    def preprocess(self):
        for k, v in self.record.items():
            self.record[k.lower()] = self.re_cdata.sub(r'\1', self.record[k])
            del self.record[k]    
    
    def get_variations(self):
        return [{'color': c} for c in self.map_colors(self.record.get('description', ''))]

    def get_description(self):
        return self.re_quote.sub('', self.record['description'])
    
    def get_image_url(self):
        return self.record['imageurl']
    
    def get_product_id(self):
        return self.record['sku']
    
    def get_gender(self):
        keyword = self.record['keywords'].split(',')[0]
        
        if keyword == 'WOMAN' or keyword == 'GIRL':
            return 'W'
        if keyword == 'MAN' or keyword == 'BOY':
            return 'M'
        
        return 'U'
    
    def get_product_name(self):
        return self.record['name']
    
    def get_availability(self):
        if self.re_yes.match(self.record['instock']) and self.re_yes.match(self.record['online']):
            return True
        
        return False
    
    def get_product_url(self):
        return self.record['buyurl']
    
    def get_category(self):
        return self.record['advertisercategory']
    
    def get_price(self):
        price = self.record.get('price')
        if price is None:
            return
        
        return self.re_price.sub('', price)
    
class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=CJMapper
        self.dialect=utils.CSVPipeDelimitedQuoted
    
