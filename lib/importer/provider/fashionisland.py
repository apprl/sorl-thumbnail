from importer.provider import Provider as ProviderBase
from importer.mapper import DataMapper
from importer.fetcher import fetch_source
from importer.parser import csv_dialects
import csv, re
from pprint import pprint


class Provider(ProviderBase):
    """
    This class is instantiated for each provider. It can to implement following 
    routines:
    
    - fetch         Retrive an object and instantiate a stream
    - process       Process the raw data and map products to the Apparel Row data model
    
    See documentation in super class importer.provider.Processor on how they
    are expected to behave.
    
    Only process needs to be specifically dealt with, the base class is designed
    to deal with most other tasks using only the configuration
    """
    
    def __init__(self, **kwargs):
        # Set configurations here
        ProviderBase.__init__(self, **kwargs)
        
        self.name      = 'fashionisland'      # Name (FIXME: derive from package?)
        self.url       = 'http://www.fashionisland.se/system/tools/dbexport/kelkoo.asp'
        self.extension = 'csv'
    
    
    def process(self):
        if not self.file:
            # FIXME: Replace with ImporterException
            raise Exception('No source file available')
        
        self.process_as_csv(
            encoding='iso-8859-1',
            fieldnames=(
                'categories',        # 0 
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
            dialect=csv_dialects.PipeDelimited,
            mapper=FashionIslandDataMapper,
        )
        


class FashionIslandCSVDialect(csv.Dialect):
    lineterminator = '\n'
    delimiter = '|'
    quoting = csv.QUOTE_NONE


class FashionIslandDataMapper(DataMapper):
    def set_sku(self, value):
        return self.data.get('product_id')
    
    def set_vendor_name(self, value):
        return 'Fashion Island'
    
    def set_categories(self, value):
        if not value:
            return
        
        if not value and 'product_name' in self.data and self.data['product_name'] == 'Leon Jacket':
            value = 'Jacket'
        
        # Strip useless pre/suffixes
        value = re.sub(ur'-?(?:F.rstasidan|erbjudanden)-?', '', value)
        
        if value in ignore_category:
            return None
        
        return [translate_category(value)]
    
    def set_product_image_url(self, value):
        if not value:
            return
        
        return re.sub(r'_(\w)\.jpg', '_L.jpg', value)
    
    
    def set_option_gender(self):
        if not 'gender' in self.data:
            return
        
        value = self.data['gender'].lower()        
        if value == 'mens':
            return 'M'
        elif value == 'womens':
            return 'F'
        else:
            # FIXME: Debug
            print "Unrecognised value: %s" % self.data['gender']
            return 'U'
    
    
    def set_option_shoesizeeu(self):
        if not 'size' in self.data:
            return
        
        if re.match(r'^\d+(?:\.5)?$', self.data['size']):
            return self.data['size']
    
    def set_option_pantslength(self):
        if not 'size' in self.data:
            return
        
        m = re.match(re_pant_size, self.data['size'])
        if m:
            return m.group(2)
        
    def set_option_pantswidth(self):
        if not 'size' in self.data:
            return
        
        m = re.match(re_pant_size, self.data['size'])
        if m:
            return m.group(1)
        
    def set_option_relativesize(self):
        if not 'size' in self.data:
            return
        
        for pair in rel_size_map:
            match = re.match(pair[1], self.data['size'])
            if match:
                if match.groups():
                    return '%s%s' % (match.group(1).upper(), pair[0])
                else:
                    return pair[0]
        
        return None
                
    def set_option_color(self):
        if not 'product_name' in self.data:
            return
        
        # FIXME: Pick color key-words from elsewhere.
        # Probalby put things like this in a "toolkit" class
        match = re.search(
            r'(black|blue|red|bronze|navy|white|gr(?:e|a)y|brown|green|svart)', 
            self.data['product_name'],
            re.I
        )
        
        if match:
            color = match.group(1).lower()
            # FIXME: Make this special casing generic
            if color == 'svart':
                color = 'black'
            
            return color
        
        return
        
    
    def set_vendor_option_currency(self):
        return 'SEK'
    
    def set_vendor_option_price(self):
        return self.data.get('delivery_price')
    
    def set_vendor_option_buy_url(self):
        return self.data.get('product_url')
        


# FIXME: Move this to other toolkit module

rel_size_map = (
    ('S', re.compile('^(x*)(?:(?:\s|-)*)s(?:mall)?$', re.I),),
    ('M', re.compile('^m(?:edium)?$', re.I),),
    ('L', re.compile('^(x*)(?:(?:\s|-)*)l(?:arge)?$', re.I),),
)

re_pant_size = re.compile('^(\d+)-(\d+)$')


category_name_map = {
    u'Cardigan-F\u00f6rstasidan': u'Cardigans',
    u'Cardigan': u'Cardigans',
    u'Wallets': u'Pl\u00e5nb\u00f6cker',
    u'Pants': u'Byxor',
    u'Bomber': u'Jackor',
    u'Sweatshirt': u'Tr\u00f6jor',
    u'Tr\u00f6ja': u'Tr\u00f6jor',
    u'Skor': u'Skor',
    u'Tank top': u'Toppar',
    u'Jackor-Skjortor': u'Skjortor',
    u'T-shirt': u'T-shirts',
    u'Bermuda shorts-Shorts': u'Shorts',
    u'Hoodie': u'Tr\u00f6jor',
    u'Belts': u'B\u00e4lten',
    u'Chinos': u'Byxor',
    u'Trunks': u'Trunks',
    u'Scarves': u'Halsdukar',
    u'Gloves': u'Handskar',
    u'Fickn\u00e4sduk': u'Accessories',
    u'Pik\u00E9': u'Shirts',
    u'Ziptr\u00f6ja': u'Tr\u00f6ja',
    u'Socks': u'Strumpor',
    u'Pullover': u'Tr\u00f6jor',
    u'Jeansskjortor-L\u00e5ng \u00e4': u'L\u00e5ng \u00e4rmat',
    u'ChinosJeans': u'Byxor',
    u'Halsdukar-M\u00f6ssor': u'M\u00f6ssor',
    u'Linne': u'Linnen',
    u'L\u00e5ng \u00e4rm': u'L\u00e5ng \u00e4rmat',
    u'Shirts': u'Skjortor',
    
}

ignore_category = [
    u'Lap top skins',
    u'F\u00f6rstasidan',
    u'INTERNAL',
    u'Trunks',
]

def translate_category(name):
    return category_name_map.get(name, name)


