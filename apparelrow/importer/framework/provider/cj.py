import re

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper
    
class CJMapper(DataMapper):
    pass

class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=CJMapper
        self.dialect=utils.CSVStandard
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

