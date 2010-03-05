from importer.provider import Provider as ProviderBase
from importer.mapper import DataMapper
from importer.fetcher import fetch_source

import libxml2, re
from xml.sax.saxutils import unescape

from pprint import pprint

class Provider(ProviderBase):
    """
    Imports product feed from Acne Jeans
    """
    
    def __init__(self, **kwargs):
        # Set configurations here
        ProviderBase.__init__(self, **kwargs)
        
        self.name      = 'acnejeans'      # Name (FIXME: derive from package?)
        self.url       = 'http://shop.acnestudios.com/system/tools/cj/feed.asp?cid=1&subid=2&aid=3&currency=SEK'
        self.extension = 'xml'
    
    def process(self):
        if not self.file:
            # FIXME: Replace with ImporterException
            raise Exception('No source file available')
        
        doc = libxml2.parseFile(self.file)
        context = doc.xpathNewContext()
        
        for elemPrd in context.xpathEval('//product'):
            # FIXME: The unescape routine only handles <, > and &. This needs
            # to be fixed.
            row = dict([(e.name, unescape(e.getContent())) for e in elemPrd.xpathEval('./*')])
            
            mapper = AcneJeansDataMapper(self, row)
            mapper.translate()
        
        context.xpathFreeContext()
        doc.freeDoc()


class AcneJeansDataMapper(DataMapper):
    
    def set_manufacturer_name(self, value):
        return 'Acne Jeans'

    def set_product_image_url(self, value):
        if not 'imageurl' in self.data:
            return
        
        substitute = re.sub(r'_(\w)\.jpg', '_L.jpg', self.data['imageurl'])
        return re.sub(r'/(\w)_', '/l_', substitute)
        
    def set_vendor_name(self, value):
        return 'Acne Jeans'
    
    def set_categories(self, value):
        if not 'advertisercategory' in self.data:
            return
        
        m = re.match('.+?>(.+)', self.data['advertisercategory'])
        if m:
            return [m.group(1)]
    
    def set_product_name(self, value):
        if not 'name' in self.data:
            return
        
        m = re.match(r'^(?:.*:\s)?(.+)$', self.data['name'])

        if m and len(m.groups()) == 1:
            return m.group(1)
        
        return m.group(0)
    
    def set_option_gender(self):
        if not 'advertisercategory' in self.data:
            return
        
        m = re.match(r'^((?:wo)?mens)>', self.data['advertisercategory'], re.I)
        if m:
            c = m.group(1).lower()
            if c == 'womens':
                return 'F'
            if c == 'mens':
                return 'M'
        
        return
    
    def set_vendor_name(self, value):
        return 'Acne Jeans'
    
    def set_vendor_option_buy_url(self):
        return self.data.get('buyurl')
    
