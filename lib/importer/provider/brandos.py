import re
from importer.provider.abstract.pricerunner import PriceRunnerProvider, PriceRunnerMapper
from importer.fetcher import fetch_source

class Provider(PriceRunnerProvider):
    """
    Imports product feed from Brandos
    """
    
    def __init__(self, **kwargs):
        # Set configurations here
        PriceRunnerProvider.__init__(self, **kwargs)
        
        self.name      = 'brandos'      # Name (FIXME: derive from package?)
        self.url       = 'http://www.brandos.se/feed/pricerunner.xml'
        self.mapper    = BrandosDataMapper


class BrandosDataMapper(PriceRunnerMapper):    
    def set_product_image_url(self, value):
        """
        Replace -m with -l to get larger product image
        """
        url = PriceRunnerMapper.set_product_image_url(self, value)
        
        return re.sub(r'-(\w)\.jpg', '-l.jpg', url)

    def set_categories(self, value):
        """
        Remove any brand name in front of category name
        Remove duplicate category listings
        """
        categories = []
        for c in value:
            m = re.match(re_split_name, c)
            if m: c = m.group(1)
            
            if not c in categories: 
                categories.append(c)
            
        return categories

    def set_product_name(self, value):
        """
        Remove brand name in front of product name
        """
        name = PriceRunnerMapper.set_product_name(self, value)
        
        m = re.match(re_split_name, name)
        if m: name = m.group(1)
        
        return name

re_split_name = re.compile(r'^.+?: (.+?)$')
