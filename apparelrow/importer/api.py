import logging, re

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

from apparel.models import *

"""
Provides an API for importing and setting up product data for the ApparelRow
web application

Synopsis

    api = API(some_data)
    api.import()
    
Required Data Structure

{
    'version': '0.1',
    'date': '2010-02-11 15:41:01 UTC',
    'vendor': 'Cali Roots',
    'product': {
        'product-id': '375512-162',
        'product-name': 'Flight 45',
        'categories': 'Sneakers',
        'manufacturer': 'Jordan',
        'price': 1399.00,
        'currency': 'SEK',
        'delivery-cost': 99.00
        'delivery-time': '3-5 D',
        'availability': True OR a number (0 for not available),
        'product-url': 'http://caliroots.com/system/search/product_vert.asp?id=20724',
        'image-url': 'http://caliroots.com/data/product/images/20724200911114162028734214_L.jpg',
        'description': 'Classic Flight 45',
        'variations':
        [
            {
                'size': '10',
                'color': 'red',
                'availability': true OR a number
            },
            ...
        ]
    }
}

 
"""

class API():
    
    def __init__(self, dataset=None):
        self.version       = "0.1"
        self._dataset      = dataset        
        self._product      = None
        self._category     = None
        self._manufacturer = None
        self._vendor       = None
        
    @property
    def dataset(self):
        """
        The API's dataset. Required before calling import() or accessing any
        data property.
        """
        if not self._dataset:
            raise IncompleteDataSet('No dataset')
        
        return self._dataset
    
    @dataset.setter
    def dataset(self, d):
        self._dataset = d
    
    @transaction.commit_on_success
    def import_dataset(self, data):
        """
        Imports the Product and related data specified in the data structure. 
        """
        
        try:
            self.validate(data)
            
            if 'product' in data:
                self.import_product(data['product'])
            
        except ImporterException, e:
            # Log ImporterException
            logging.error('%s, record skipped', e)
            raise
        else:
            logging.info('Imported %s', self.product)
    
    
    
    def validate(self):
        """
        Validates a data structure. Returns True on success, will otherwise throw
        an exception
        """
        
        if self.dataset.get('version') != self.version:
            raise ImporterException('Incompatable version number "%s" (this is version %s)', self.dataset.get('version'), self.version)
        
        logging.debug('Dataset is valid')
        return True
    
    
    @property
    def category(self):
        """
        Returns category. Category hierarchy is retrieved or created first time
        the property is accessed.
        """
        
        if not self._category:        
            category_names = self.dataset['product'].get('categories')
            
            if not category_names:
                raise IncompleteDataSet('No category')
            
            # Force list
            if not isinstance(category_names, list):
                category_names = [category_names]
            else:
                category_names.reverse()
            
            categories = []
            
            for name in category_names:
                try:
                    category = Category.objects.get(key=Category.key_for_name(name))
                except ObjectDoesNotExist:
                    logging.debug('Creating new category: %s', name)
                    category = Category( name=name )
                else:
                    logging.debug('Using existing category: %s', category.name)
                    break
                finally:
                    if len(categories) > 0:
                        logging.debug('Assigning child category %s to %s', category, categories[0].parent)
                        categories[0].parent = category
                    
                    categories.insert(0, category)
            
            if len(categories) == 0:
                raise ImporterException('Could not retrieve or create any categories')
            
            for category in categories:
                # FIXME: Is this required?
                category.save()
            
            logging.debug('Using category %s', categories[-1])
            
            self._category = categories[-1]
        
        return self._category
            
    @property 
    def manufacturer(self):
        """
        Retrieves, or creates, the product's manufacturer.
        """
        
        if not self._manufacturer:
            name = self.dataset['product'].get('manufacturer')
            
            if not name: 
                raise IncompleteDataSet('Missing manufacturer name')
            
            self._manufacturer, created = Manufacturer.objects.get_or_create(name=name)
            
            if created: 
                logging.debug('Created new manufacturer')
            
            logging.debug('Using manufacturer %s', name)
        
        return self._manufacturer
    
    @property
    def vendor(self):
        """
        Retrives, or creates, the vendor of this dataset
        """
        
        if not self._vendor:
            name = self.dataset.get('vendor')
         
            if not name:
                raise IncompleteDataSet('Missing vendor name')
            
            self._vendor, created = Vendor.objects.get_or_create(name=name)
            
            if created:
                logging.debug('Created new vendor')
            
            logging.debug('Using vendor %s', name)
        
        return self._vendor




class ImporterException(Exception):
    """
    An exception base class that will prevent the current data to be imported
    and any change to be rolled back.
    """
    pass

class SkipProduct(ImporterException):
    """
    For some reason the product should be skipped.
    """
    pass

class IncompleteDataSet(ImporterException):
    """
    The product could not be imported because required data is missing or 
    malformatted.
    """
    pass

