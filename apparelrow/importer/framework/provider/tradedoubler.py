import re

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper

# Columns:
#   warranty
#   isbn
#   weight
#   currency
#   productUrl
#   TDProductId
#   shortDescription
#   availability
#   manufacturer
#   merchantCategoryName
#   sku
#   shippingCost
#   TDCategoryName
#   previousPrice
#   inStock
#   size
#   price
#   description
#   ean
#   mpn
#   extraImageProductLarge
#   brand
#   extraImageProductSmall
#   programId
#   programLogoPath
#   color
#   programName
#   date
#   promoText
#   condition
#   advertiserProductUrl
#   techSpecs
#   name
#   deliveryTime
#   fields
#   imageUrl
#   upc
#   TDCategoryID
#   gender
#   model

class TradeDoublerMapper(DataMapper):
    re_split = re.compile(r'(?<!http):')
    genders  = {'Man': 'M', 'Kvinna': 'F'}
    
    def preprocess(self):
        self.record.update([self.re_split.split(v) for v in self.record.get('fields', '').split(';')])
    
    def map_variations(self):
        c = self.map_colors(self.record.get('color'))
        self.record['variations'] = [{
            'color': c[0] if len(c) else None,
            'gender': self.genders.get(self.record.get('gender'), 'U'),
        }]
    
    def get_product_name(self):
        return self.record.get('product-name')
    
    def get_product_id(self):
        return self.record.get('TDProductId')
    
    def get_category(self):
        return self.record.get('merchantCategoryName', self.record.get('TDCategoryName'))
    
    def get_manufacturer(self):
        return self.record.get('manufacturer', self.record.get('brand'))
    
    def get_product_url(self):
        return self.record.get('product-url')
    
    def get_delivery_cost(self):
        return self.record.get('shippingCost', '').split(' ')[0]
        
    def get_delivery_time(self):
        return self.record.get('deliveryTime')
        
    def get_availability(self):
        return True if self.record.get('availability') else False
        
    def get_image_url(self):
        return self.record.get('extraImageProductLarge', self.record.get('extraImageProductSmall'))
        
    # FIXME: Parse HTML entities in description
    
class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=TradeDoublerMapper
        self.dialect=utils.CSVPipeDelimitedQuoted
        self.encoding='iso-8859-1'
