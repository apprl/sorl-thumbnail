import re

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper
    
class GrandpaMapper(DataMapper):
    def get_description(self):
        d = self.record.get('description')
        # FIXME: Remove embedded HTML.
        # FIXME: Should that be done generically?
        return re.sub(ur'-|_{2,}', '', d)

    def get_variations(self):
        variations = []
        for color in self.map_colors(self.record.get('product-name', '')):
            #FIXME: should do a check for availability instead of just None (No information)
            variations.append({'color': color, 'availability': None})
        return variations

    def get_availability(self):
        return None

    def get_image_url(self):
        # FIXME: Do a HEAD for the resulting URL to ensure it exists before returning this URI
        return re.sub(r'/images/\w/', '/images/XL/', self.record.get('image-url'))

    def get_price(self):
        return self._split_price()[0]
    
    def get_currency(self):
        return self._split_price()[1]
    
    def _split_price(self):
        p = self.record.get('price')
        
        if p:
            r = re.search(r'(\d+) (\w{3})$', p)
            return r.groups()
        
        return (None, None)

class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=GrandpaMapper
        self.dialect=utils.CSVSemiColonDelimited
        self.fieldnames=(
            'category',          # 0 
            'manufacturer',      # 1 
            'product-name',      # 2 
            'product-id',        # 3 
            'price',             # 4 
            'UNKNOWN#1',         # 5
            'delivery-time',     # 6 
            'UNKNOWN#2',         # 7
            'product-url',       # 8 
            'image-url',         # 9 
            'description',       # 10
        )
    
