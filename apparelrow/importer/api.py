import logging, re

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

from apparel.models import *

"""
Provides an API for importing and setting up product data for the ApparelRow
web application

Synopsis

    api = API(some_data)
    api.import_dataset()
    
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
        
    @transaction.commit_on_success
    def import_dataset(self, data=None):
        """
        Imports the Product and related data specified in the data structure. 
        """
        
        try:
            if data:
                self.dataset = data
            
            self.validate()
            self.import_product()
        
        except ImporterException, e:
            # Log ImporterException
            logging.error('%s, record skipped', e)
            raise
        else:
            logging.info('Imported %s', self.product)
    
    
    def import_product(self):
        """
        Imports the product
        """
        
        # Download and store product image 
        fields = {
            'product_name': self.dataset['product'].get('product-name'),
            'description': self.dataset['product'].get('description'),
        }

        
        try:
            p = Product.objects.get(
                manufacturer__id__exact=self.manufacturer.id,
                sku__exact=self.dataset['product']['product-id']
            )
        except ObjectDoesNotExist:
            # Create product
            p = Product.objects.create(
                manufacturer=self.manufacturer, 
                sku=self.dataset['product']['product-id'],
                **fields
            )
            
            p.category.add( self.category )
            logging.debug('Created new product')
            
        except MultipleObjectsReturned:
            s = 'There are more than one product with sku %s for manufacturer %s' % (self.manufacturer.name, self.fields['sku'])
            logging.error(s)
            raise SkipRecord(s)
        else:
            # Update product
            for f in fields:
                setattr(p, f, fields.get(f))
            
            
            # FIXME: How do we deal with category? Re-assign?
            logging.debug('Updated product')
        
        
        # Store product variants
        #self.map_product_options()
        # Store vendor options
        #self.map_vendor_options()
        self.__vendor_options(p)
        
        p.save()
        return p
    
    
    def __vendor_options(self, product):
        """
        Private method that adds, update and maintain vendor data and options
        for a particular product
        """
        
        
        vp, created = VendorProduct.objects.get_or_create( product=product, vendor=self.vendor )
        
        if created:
            logging.debug('Added product data to vendor: %s', vp)

        # FIXME: Map
        #   - availability
        #   - delivery time
        #   - delivery cost (Property of vendor?)
        
        fields = {
            'buy_url': self.dataset['product'].get('product-url'),
            'price': self.dataset['product'].get('price'),
            'currency': self.dataset['product'].get('currency'),            
        }
        
        for f in fields:
            setattr(vp, f, fields[f])
        
        vp.save()
    
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

