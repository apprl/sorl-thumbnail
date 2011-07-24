import re

from importer.api import SkipProduct
from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper

AVAILABILITY_MATRIX = {'n': False, 'no': False, 'not in stock': False}

class TradeDoublerMapper(DataMapper):
    re_split = re.compile(r'(?<!http):')
    
    def preprocess(self):
        self.record.update([self.re_split.split(v) for v in self.record.get('fields', '').split(';')])
 
    def get_variations(self):
        variations = [{'color': c} for c in self.map_colors(self.record.get('name', ''))]
        for variation in variations:
            variation['availability'] = True if self.record.get('availability') else False
        return variations
    
    def get_gender(self):
        return self.map_gender(self.record.get('gender'))
    
    def get_product_name(self):
        return self.record.get('name')
    
    def get_product_id(self):
        return self.record.get('TDProductId')
    
    def get_category(self):
        return self.record.get('merchantCategoryName') or self.record.get('TDCategoryName')
    
    def get_manufacturer(self):
        return self.record.get('brand') or self.record.get('manufacturer')
    
    def get_product_url(self):
        return self.record.get('productUrl')
        
    def get_delivery_cost(self):
        return self.record.get('shippingCost', '').split(' ')[0]
        
    def get_delivery_time(self):
        return self.record.get('deliveryTime')
    
    def get_availability(self):
        availability = self.record.get('availability')
        if availability:
            if AVAILABILITY_MATRIX.get(availability.strip().lower(), True):
                try:
                    availability = int(availability)
                except ValueError:
                    availability = -1
                return availability
            else:
                return 0

        return None

    def get_image_url(self):
        return self.record.get('extraImageProductLarge') or self.record.get('extraImageProductSmall') or self.record.get('imageUrl')

    
class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=TradeDoublerMapper
        self.dialect=utils.CSVPipeDelimitedQuoted
        self.encoding='iso-8859-1'
