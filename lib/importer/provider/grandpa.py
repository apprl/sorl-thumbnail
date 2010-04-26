from importer.provider import Provider as ProviderBase
from importer.mapper import DataMapper, SkipRecord
from importer.fetcher import fetch_source
from importer.parser import csv_dialects

import csv, re
from pprint import pprint


class Provider(ProviderBase):
    """
    See documentation in super class
    """
    
    def __init__(self, **kwargs):
        # Set configurations here
        ProviderBase.__init__(self, **kwargs)
        
        self.name      = 'grandpa'      # Name (FIXME: derive from package?)
        self.url       = 'http://www.grandpa.se/system/tools/kelkoo/product-feed.asp'
        self.extension = 'csv'
    
    
    def process(self):
        if not self.file:
            # FIXME: Replace with ImporterException
            raise Exception('No source file available')
        
        self.process_as_csv(
            encoding='utf-8',
            fieldnames=(
                'categories',        # 0 
                'manufacturer_name', # 1 
                'product_name',      # 2 
                'product_id',        # 3 
                'price',             # 4 
                'UNKNOWN#1',         # 5
                'delivery_time',     # 6 
                'UNKNOWN#2',         # 7
                'product_url',       # 8 
                'product_image_url', # 9 
                'description',       # 10
            ),
            dialect=csv_dialects.SemiColonDelimited,
            mapper=GrandpaDataMapper,
        )
        


class GrandpaDataMapper(DataMapper):
    def set_sku(self, value):
        return self.data.get('product_id')
    
    def set_vendor_name(self, value):
        return 'Grandpa'
    
    def set_manufacturer_name(self, value):
        if value in invalid_manufacturers:
            raise SkipRecord("Invalid manufacturer %s" % value)        

        return value
    
    def set_categories(self, value):
        if not value:
            return
        
        value = re.sub(ur'\s*\(0\)$', '', value)   # Remove trailing "(0)"
        
        categories = value.split('/')
        
        if categories[-1] in invalid_categories:
            raise SkipRecord("Invalid category %s" % categories[-1])
        
        return map(lambda x: translate_category(x), categories)
    
    def set_description(self, value):
        if not value:
            return
        
        value = re.sub(ur'-{2,}', '', value) # Remove occurances or ---
        # FIXME: Remove embedded HTML
        return value
    
    
    def set_product_image_url(self, value):
        if not value:
            return

        return re.sub(r'/images/(\w)/', '/images/XL/', value)
    
    
    def set_option_gender(self):
        # Does not exist
        pass    
    
    def set_option_color(self):
        pass
        
    def set_vendor_option_currency(self):        
        price = self._get_price_currency()
        return price[1]
    
    def set_vendor_option_price(self):
        price = self._get_price_currency()
        return price[0]
    
    def set_vendor_option_buy_url(self):
        return self.data.get('product_url')
    
    def _get_price_currency(self):
        price = self.data.get('price')
        
        if price:
            r = re.search('^(\d+) (\w{3})$', price)
            if r: return r.groups()
        
        return (None, None)


invalid_manufacturers = (
    u'ACCESOARER',
    u'Prylar',
    u'AUTOUPPLAGD',
    u'\u00D6VRIGA',
)

invalid_categories = (
    u'Presenter-Spel',
    u'Spel',
    u'Inredning',
    u'Inredning-Presenter',
    u'Inredning-Presenter-Spel',
    u'Inredning-K\u00F6k',
    u'Cyklar',
    u'B\u00F6cker',
    u'B\u00F6cker-Presenter',
)
    
category_name_map = {
    u'Blusar':  'Blouses',
    u'Byxor':  'Pants',
    u'Ekologiskt-T-shirts':  'T-Shirts',
    u'Glas\u00f6gon':  'Glasses',
    u'Halsdukar':  'Scarfs',
    u'Handskar':  'Gloves',
    u'Hattar':  'Hats',
    u'Jackor':  'Jackets',
    u'Jeans-Strumpbyxor':  'Pantyhoses',
    u'Kappor':  'Coat',
    u'Kappor-Kavajer':  'Jackets',
    u'Kavajer':  'Jackets',
    u'Kavajer-Kl\u00e4nning':  'Dresses',
    u'Kavajer-Tr\u00f6jor':  'Sweaters',
    u'Kjolar':  'Skirts',
    u'Klockor':  'Watches',
    u'Kl\u00e4nning':  'Dresses',
    u'Linnen':  'Linen',
    u'M\u00f6ssor':  'Caps',
    u'Pl\u00e5nb\u00f6cker':  'Wallts',
    u'Rockar':  'Coats',
    u'Skjortor':  'Shirts',
    u'Skor':  'Shoes',
    u'Sk\u00e4rp':  'Belts',
    u'Smycken':  'Jewellry',
    u'Solglas\u00f6gon':  'Sunglasses',
    u'Spel':  'Games',
    u'Stickat':  'Knitted',
    u'Strumpbyxor':  'Pantyhoses',
    u'Strumpor':  'Socks',
    u'Toppar':  'Tops',
    u'Tr\u00f6jor':  'Sweaters',
    u'Vantar':  'Gloves',
    u'V\u00e4skor':  'Bags',
    u'skjortor':  'Shirts',
    u'skjortor-Kl\u00e4nning':  'Dresses',
    u'Jewellry': 'Jewelry',
}

def translate_category(name):
    return category_name_map.get(name, name)



