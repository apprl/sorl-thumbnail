import re, logging, datetime
from apparelrow.importer.api import API, SkipProduct, ImporterException



class DataMapper():
    
    def __init__(self, provider, record={}):
        self.provider     = provider    # Reference to the provider instance
        self.record       = record      # Raw data record source file
    
    def map_variations(self):
        """
        Should map variations and store them in self.record['variations']
        """
        pass
        
    
    def translate(self):
        """
        Returns a hash of correctly formatted fields
        """
        
        # Product fields
        
        api_dict = {
            'version': '0.1',
            'date':    self.map_field('date') or datetime.datetime.now().strftime('%Y-%m-%dT%H:%m:%SZ%z'),
            'vendor':  self.provider.feed.vendor.name,
            'product': {}
        }
        
        for field in ['product-id', 
                      'product-name', 
                      'categories', 
                      'manufacturer', 
                      'price', 
                      'currency', 
                      'delivery-cost', 
                      'delivery-time', 
                      'image-url', 
                      'product-url', 
                      'description', 
                      'availability']:
            try:
                api_dict['product'][field] = self.map_field(field)
            except SkipField:
                logging.debug('Skipping field %s' % field)
                continue
        
        self.map_variations()
        api_dict['product']['variations'] = self.record.get('variations', [])
        
        return api_dict
        
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



def _trim(value):
    if value is None:
        return value
    
    repl = lambda x: re.sub(r'^\s*|\s*$', '', x)
    
    if isinstance(value, list):
        value = map(repl, value)
    else:
        value = repl(value)
    
    return value

class SkipField(Exception):
    pass
