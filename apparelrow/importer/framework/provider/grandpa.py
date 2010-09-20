import re

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper


#  {
#      'version': '0.1',
#      'date': '2010-02-11 15:41:01 UTC',
#      'vendor': 'Cali Roots',
#      'product': {
#          'product-id': '375512-162',
#          'product-name': 'Flight 45',
#          'categories': 'Sneakers',
#          'manufacturer': 'Jordan',
#          'price': 1399.00,
#          'currency': 'SEK',
#          'delivery-cost': 99.00,
#          'delivery-time': '3-5 D',
#          'availability': True OR a number (0 for not available),
#          'product-url': 'http://caliroots.com/system/search/product_vert.asp?id=20724',
#          'image-url': 'http://caliroots.com/data/product/images/20724200911114162028734214_L.jpg',
#          'description': 'Classic Flight 45',
#          'variations':
#          [
#              {
#                  'size': '10',
#                  'color': 'red',
#                  'availability': true OR a number
#              },
#              ...
#          ]
#      }
#  }

class GrandpaMapper(DataMapper):
    def get_description(self):
        d = self.record.get('description')
        # FIXME: Remove embedded HTML.
        # FIXME: Should that be done generically?
        return re.sub(ur'-|_{2,}', '', d)
    
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
            'categories',        # 0 
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




