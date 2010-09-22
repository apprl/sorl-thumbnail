import re

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper

class KelkooMapper(DataMapper):
    def map_variations(self):
        for variation in self.record['variations']:
            variation['availability'] = self.record.get('available') or True
            
            c = self.map_colors(self.record.get('product-name'))
            if len(c): variation['color'] = c[0]
    
    
    def get_currency(self):
        return 'SEK'
    
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
            'categories',        # 0 
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
        return self.record.get('product-url') == new_record.get('product-url')
    
    def merge(self, new_record):
        if not 'variations' in self.record:
            self.record['variations'] = []
        
        self.record['variations'].append({'size': new_record.get('size')})


