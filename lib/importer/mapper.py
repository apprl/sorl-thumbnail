import re, traceback, sys, logging
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files import File
from django.template.defaultfilters import slugify
from apparel.models import *
from importer import fetcher
from urllib2 import HTTPError


# FIXME: Move to Django settings directory
PRODUCT_IMAGE_BASE = 'static/product'


class DataMapper():
      
    def __init__(self, provider, data={}):
        self.data         = data
        self.provider     = provider  # Reference to the provider instance
    
    def translate(self):
        """
        Runs the actual mapping process and does following things (in order)
        """
        
        logging.debug('*** Start mapping raw product data ***'.upper())
        mapped = dict()
        
        try:
            self.map_fields()    
            self.map_manufacturer()
            self.map_category()
            self.map_vendor()
            self.map_product()
        
        except SkipRecord, e:
            logging.error("Skipping record: %s", e)
            self.log_error('skip', e)
    
        except Exception, e:
            logging.critical("Caught fatal exception")
            logging.exception(e)
            self.log_error('fatal', e)
            
            raise e
        
        logging.info('Processed product %s', self.product)
        
        return mapped
    

        
def _trim(value):
    if value is None:
        return value
    
    repl = lambda x: re.sub(r'^\s*|\s*$', '', x)
    
    if isinstance(value, list):
        value = map(repl, value)
    else:
        value = repl(value)
    
    return value



class SkipRecord(Exception):
    """
    Raising this exception will cause the current record to be ignored, and no
    product created.
    """

    def __init__(self, reason):
        if reason is None:
            raise Exception("Need reason to raise SkipRecord")
        
        Exception.__init__(self, reason)

