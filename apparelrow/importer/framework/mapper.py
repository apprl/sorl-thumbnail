import re, logging, datetime
from apparelrow.importer.api import API, SkipProduct, ImporterException



class DataMapper():
    
    def __init__(self, provider, record={}):
        self.provider     = provider    # Reference to the provider instance
        self.record       = record      # Raw data record source file
        self.variances    = []          # Product variances
    
    
    def translate(self):
        """
        Maps a record (a flat dict) parsed from source file to a hash readable
        by the API. The mapping follows the following procedure
        
            add_variances()     Returns list of variances extracted from record
            map_fields()        Returns the API friendly data structure
            store_product()     Calls the API with the product
        
        """
        
        p = None
        
        try:
            p = API().import_dataset( self.map_fields() )
        
        except SkipRecord, e:
            logging.info('Record skipped: %s', e)
        
        except ImporterException, e:
            logging.error('Record skipped due to importer errors: %s', e)

        except Exception, e:
            logging.critical('Translation failed with uncaught exception: %s', e)
            raise 
        else:
            logging.info('Imported product %s', p)

    
    def add_variances(self):
        """
        Adds a list of variances to the 'variances' array.
        """
        # FIXME: Should we simply let the parser to this, and leave it out
        # of here. Something along the lines of
        #   for record in parse_source:
        #       m = Mapper(record)
        #       m.variances.append(record['var1'])
        #       m.variances.append(record['var2'])
        #       m.translate()
        
        # Currently the base class implementation does nothing
        pass
        
    
    def map_fields(self):
        """
        Returns a hash of correctly formatted fields
        """
        
        # Product fields
        
        api_dict = {
            'version': '0.1',
            'date':    self.map_field('date') or datetime.datetime.now().strftime('%Y-%m-%dT%H:%m:%SZ%z'),
            'vendor':  self.provider.name,
            'product': {}
        }
        
        # FIXME: Get field list from somewhere else
        for field in ['product-id', 'product-name', 'categories', 'manufacturer', 
                  'price', 'currency', 'delivery-cost', 'delivery-time', 
                  'image-url', 'product-url', 'description']:
            try:
                api_dict['product'][field] = self.map_field(field)
            except SkipField:
                logging.debug('Skipping field %s' % field)
                continue
        
        api_dict['product']['variances'] = self.add_variances() or []
        
        return api_dict
        
    def map_field(self, field_name):
        """
        Returns a value for the given field. This method will first try to call
        a method called
        
            self.set_[field_name]
        
        (Note: Any occurence of - in the field name is represented by _ in the
        method name. So for field 'product-name', this method will attempt to
        call 'set_product_name')
        
        and if that does not exist it will try use a value stored in:
        
            self.record[field_name]
        
        else return None
        
        This method may throw a SkipField exception causing the field to be 
        skipped, but the process to continue.
        """
        
        method_name = 'set_%s' % field_name.replace('-', '_')
        
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
