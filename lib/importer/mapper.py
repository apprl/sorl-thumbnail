import re, traceback, sys, logging
<<<<<<< HEAD:lib/importer/mapper.py
from apparelrow.importer.api import API, SkipRecord, ImporterException
=======
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files import File
from django.template.defaultfilters import slugify
from apparel.models import *
from importer import fetcher
from urllib2 import HTTPError, URLError
>>>>>>> 021142f3f90de00b51ca8c3332e86cb620095e8a:lib/importer/mapper.py



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
            self.add_variances()

            p = API().import_dataset( self.map_fields() )
        
        except SkipRecord, e:
<<<<<<< HEAD:lib/importer/mapper.py
            logging.info('Record skipped: %s', e)
=======
            # FIXME: Add logging here. Require the SkipRecord exception to carry a name with the reason
            logging.error("Skipping record: %s", e)
            self.rollback()
        except HTTPError, e:
            pass
        except Exception, e:
            # FIXME: For debugging purposes, we might not want a rollback to 
            # happen here, let this be an option
            logging.critical("Caught fatal exception")
            self.rollback()
            logging.exception(e)
            raise e
        else:        
            logging.info('Processed product %s', self.product)
    
    def map_fields(self):
        """
        Maps the data in self.data to the self.fields list that will be used to
        create related objects.
        """
        
        if not isinstance(self.data, dict):
            raise ValueError('data property is expected to be a dictionary')
        
        logging.debug(self.data)
        
        for attr in self.fields.keys():
            # If there is a set_... method, use it to return the value, otherwise
            
            value = self.data[attr] if attr in self.data else None
            
            if hasattr(self, 'set_%s' % attr):
                value = getattr(self, 'set_%s' % attr)(value)
            
            self.fields[attr] = _trim(value)
            
            logging.debug('Mapped product field %s to %s', attr, value)
    
    def map_manufacturer(self):
        """
        Attempts to locate manufacturer matching the collected. If it can't, a
        new one will be created.
        """
        
        name = self.fields['manufacturer_name']
        
        if not name:
            raise SkipRecord('Manufacturer name not mapped')
        
        self.manufacturer, created = Manufacturer.objects.get_or_create(name=name)
        
        if created:
            logging.debug('Created new manufacturer: %s', name)
>>>>>>> 021142f3f90de00b51ca8c3332e86cb620095e8a:lib/importer/mapper.py
        
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
        
        return {}
        
    def map_field(self, field_name):
        """
        Returns a value for the given field. This method will first try to call
        a method called
        
            self.get_[field_name]
        
        and if that does not exist it will try use a value stored in
        
<<<<<<< HEAD:lib/importer/mapper.py
            self.record[field_name]
=======
        if not default_storage.exists(sitepath):
            logging.info('Downloading product image %s', url)
            temppath = None
            
            try:
                temppath = fetcher.fetch(url)
            except (HTTPError, URLError), e:
                logging.error('%s (while downloading %s', e, url)
                return
            
            default_storage.save(sitepath, File(open(temppath)))
            logging.debug("Stored %s", sitepath)
        else:
            logging.debug('Image %s already exists, will not download', sitepath)
>>>>>>> 021142f3f90de00b51ca8c3332e86cb620095e8a:lib/importer/mapper.py
        
        else return None
        
        This method may throw a SkipField exception causing the field to be 
        skipped, but the process to continue.
        """
        pass
    



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
