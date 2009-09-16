from importer.provider import Processor as ProcessorBase
from importer.mapper import DataMapper

import csv, re

from pprint import pprint


class Processor(ProcessorBase):
    """
    This class is instantiated for each provider. It can to implement following 
    routines:
    
    - fetch         Retrive an object and instantiate a stream
    - process       Process the raw data and map products to the Apparel Row data model
    - archive       Archive the file
    
    See documentation in super class importer.provider.Processor on how they
    are expected to behave.
    
    Only process needs to be specifically dealt with, the base class is designed
    to deal with most other tasks using only the configuration
    
    """
    
    def __init__(self, **kwargs):
        # Set configurations here
        self.name       = 'fasionisland'      # Name (FIXME: derive from package?)
        self.file       = None                # A stream object
    
    def fetch(self):
        # FIXME: Fetch the file from the INTERNET
        self.file = open('data.csv')
    
    
    def process(self):
        
        if not self.file:
            # FIXME: Replace with ImporterException
            raise Exception('No source file available')
    
        self.process_csv(
            source=self.file,
            encoding='iso-8859-1',
            fieldnames=(
                'category_name',     # 0 
                'manufacturer_name', # 1 
                'product_name',      # 2 
                'size',              # 3 
                'product_id',        # 4 
                'price',             # 5 
                'delivery_price',    # 6 
                'delivery_time',     # 7 
                'available',         # 8 
                'product_url',       # 9 
                'product_image_url', # 10 
                'description',       # 11
                'gender',            # 12
            ),
            dialect=FasionIslandCSVDialect,
            mapper=FasionIslandDataMapper,
        )
        


class FasionIslandCSVDialect(csv.Dialect):
    lineterminator = '\n'
    delimiter = '|'
    quoting = csv.QUOTE_NONE


class FasionIslandDataMapper(DataMapper):
    def set_sku(self, value):
        
        if 'product_id' in self.data:
            return self.data['product_id']
    
        return None
    
    def set_category_name(self, value):
        if not value:
            return
        
        if not value and 'product_name' in self.data and self.data['product_name'] == 'Leon Jacket':
            return 'Jacket'
        
        # Strip useless pre/suffixes
        value = re.sub(ur'-?(?:F.rstasidan|erbjudanden)-?', '', value)
        
        # Remove double "T-shirt"
        value = re.sub(r'T-shirt-(?=T-shirts)', '', value)
        
        # Always in plural
        value = re.sub(r'^T-shirt$', 'T-shirts', value)
        
        return value
    
    def set_gender(self, value):
        if value.lower() == 'mens':
            return 'M'
        elif value.lower() == 'womens':
            return 'F'
        else:
            print "Unrecognised value: %s" % value
            return 'U'

