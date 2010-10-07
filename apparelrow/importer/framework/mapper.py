import re, logging, datetime, htmlentitydefs

from django.conf import settings

from apparelrow.importer.api import API, SkipProduct

logger = logging.getLogger('apparel.importer.mapper')


class DataMapper():
    
    color_regexes = None
    re_html     = re.compile(r'<.+?>', re.S)
    re_trunc_ws = re.compile(r'[ \t\r]{2,}')
    re_trim     = re.compile(r'^\s*|\s*$')
    
    def __init__(self, provider, record={}):
        self.provider      = provider    # Reference to the provider instance
        self.record        = record      # Raw data record source file
        self.mapped_record = {}
    
    def preprocess(self):
        """
        This method is called immidiately before field mapping begins. The 
        current record can be found in self.record.
        Does not expect any return value.
        """
        pass
    
    def postprocess(self):
        """
        This method is called immidiately after field mappings are complete. The
        mapped data can be found in self.mapped_record, and the raw data in 
        self.record
        
        By default, postprocess performs following actions
        
         * Leading and trailing whitespaces are trimmed
         * HTML is stripped from the description field
         * HTML entities are expanded to unicode characters in the description field
        
        """
        
        for field, value in self.mapped_record['product'].items():
            self.mapped_record['product'][field] = self.trim(value)
        
        self.mapped_record['product']['description'] = self.strip_html(self.mapped_record['product']['description'])
    
    def translate(self):
        """
        Returns a hash of correctly formatted fields
        """
        
        self.preprocess()
        
        self.mapped_record.update({
            'version': '0.1',
            'date':    self.map_field('date') or datetime.datetime.now().strftime('%Y-%m-%dT%H:%m:%SZ%z'),
            'vendor':  self.provider.feed.vendor.name,
            'product': {}
        })
        
        for field in ('product-id', 
                      'product-name', 
                      'category',
                      'manufacturer', 
                      'price', 
                      'gender',
                      'currency', 
                      'delivery-cost', 
                      'delivery-time', 
                      'image-url', 
                      'product-url', 
                      'description', 
                      'availability',):
            try:
                self.mapped_record['product'][field] = self.map_field(field)
            except SkipField:
                logger.debug('Skipping field %s' % field)
                continue
        
        self.mapped_record['product']['variations'] = self.map_field('variations') or []
        
        self.postprocess()
        
        return self.mapped_record
    
    def map_field(self, field_name):
        """
        Returns a value for the given field. This method will first try to call
        a method called
        
            self.get_[field_name]
        
        (Note: Any occurence of - in the field name is represented by _ in the
        method name. So for field 'product-name', this method will attempt to
        call 'get_product_name')
        
        and if that does not exist it will try use a value stored in:
        
            self.record[field_name]
        
        else return None
        
        This method may throw a SkipField exception causing the field to be 
        skipped, but the process to continue.
        """
        
        method_name = 'get_%s' % field_name.replace('-', '_')
        
        if hasattr(self, method_name):
            return getattr(self, method_name)()
       
        return self.record.get(field_name)
    
    #
    # - Helper methods -
    #
    
    def map_colors(self, value=""):   
        """
        Helper method that appempts to extract colour names from the given string
        and returns a list of names known by apparelrow.
        
        Example
        
        >>> mapper = DataMapper()
        >>> list = mapper.map_colors(u'Here is a string with Black, navy and red')
        ['black', 'blue', 'red']
        """
        
        if not self.color_regexes:
            # Compile regular expression matching all aliases to a color first time
            # this method is accessed.
            self.color_regexes = dict(
                (c[0], re.compile(r'\b(?:%s)\b' % '|'.join(c), re.I))
                for c in settings.APPAREL_IMPORTER_COLORS
            )
        
        return [c for c, r in self.color_regexes.items() if r.search(value)]
    
    
    def strip_html(self, text):
        """
        Strings argument from all HTML-tags and expands HTML entities.
        """
        
        return self.trim(
                    expand_entities(
                        self.re_html.sub(
                            ' ', 
                            text
                        )
                    )
                )
            
    def trim(self, text):
        """
        Trims whitespaces to the left and right of text. Argument may be a list
        of strings which will be trimmed.
        """
        
        repl = lambda x: self.re_trunc_ws.sub(' ', self.re_trim.sub('', x))
        
        try:
            if isinstance(text, list):
                text = map(repl, text)
            else:
                text = repl(text)
        except TypeError:
            pass
                
        return text

def expand_entities(text):
    """
    Expands HTML entities from the given text.
    Written by Fredrik Lundh, http://effbot.org/zone/re-sub.htm#unescape-html
    """
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        
        return text # leave as is
    
    return re.sub("&#?\w+;", fixup, text)


class SkipField(Exception):
    """
    This is raised by a field mapper causing the field not to be mapped.
    """
    pass
