import re

from importer.framework.provider.cj import CJMapper, Provider as CJProvider

# See documentation in cj.py for info on feed format

class YooxMapper(CJMapper):
    re_name = re.compile('\s+-\s+at\s+yoox\.com\s*', re.I)
    re_list = re.compile('(?<=\w)\s+(?=[A-Z])')         # Matches the space between a words followed by a capitalised word
    re_yoox = re.compile('\sYOOX$', re.I)
    
    def get_description(self):
        return self.re_list.sub(', ', super(YooxMapper, self).get_description())
        
    def get_category(self):
        categories = self.record['keywords'].split(',')[2:4]
        self.re_yoox.sub('', categories[1])
        
        return '/'.join(categories)
        
    def get_product_name(self):
        return self.re_name.sub('', super(YooxMapper, self).get_product_name())
    

class Provider(CJProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=YooxMapper
