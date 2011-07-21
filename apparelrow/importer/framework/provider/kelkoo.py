import re

from django.template.defaultfilters import slugify

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper

AVAILABILITY_MATRIX = {'n': False, 'no': False, 'not in stock': False}

def parse_product_id(record):
    return record.get('product-id') or slugify(record.get('product-url'))

class KelkooMapper(DataMapper):
    genders = {'Mens': 'M', 'Womens': 'W'}

    def get_variations(self):
        for variation in self.record['variations']:
            variation['availability'] = self.record.get('available') or None
            
            c = self.map_colors(self.record.get('product-name', ''))
            if len(c): variation['color'] = c[0]
        
        return self.record['variations']

    def get_availability(self):
        availability = self.record.get('available')
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
   
    def get_product_id(self):
        return parse_product_id(self.record)
    
    def get_currency(self):
        return 'SEK'
    
    def get_gender(self):
        return self.genders.get(self.record.get('gender'))
    
    def get_image_url(self):
        try:
            return re.sub(r'_(\w)\.jpg', '_L.jpg', self.record['image-url'])
        except KeyError, e:
            return None
    

class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=KelkooMapper
        self.dialect=utils.CSVPipeDelimited
        self.encoding='iso-8859-1'
        self.fieldnames=(
            'category',          # 0 
            'manufacturer',      # 1 
            'product-name',      # 2 
            'size',              # 3 
            'product-id',        # 4 
            'price',             # 5 
            'delivery-price',    # 6 
            'delivery-time',     # 7 
            'available',         # 8 
            'product-url',       # 9 
            'image-url',         # 10 
            'description',       # 11
            'gender',            # 12
        )
    
    
    def should_merge(self, new_record):
        return parse_product_id(self.record) == parse_product_id(new_record)
    
    def merge(self, new_record):
        if not 'variations' in self.record:
            self.record['variations'] = []
        
        self.record['variations'].append({'size': new_record.get('size')})


