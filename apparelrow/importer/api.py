import logging, re, tempfile, urllib2, os

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files.storage import default_storage
from django.template.defaultfilters import slugify
from django.db import transaction
from django.db.models import Count
from django.conf import settings
from urllib2 import HTTPError

from apparel.models import *
from importer.framework.fetcher import fetch

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
        'delivery-cost': 99.00,
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

class API(object):
    re_url = re.compile(r'^.+/(.+)$')
    
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
        
        p = None
        
        try:
            if data:
                self.dataset = data
            
            self.validate()
            p = self.import_product()
        
        except ImporterException, e:
            # Log ImporterException
            logging.error('%s, record skipped', e)
            raise
        else:
            logging.info('Imported %s', p)
            return p
    
    
    def import_product(self):
        """
        Imports the product
        """
        
        # Download and store product image 
        fields = {
            'product_name': self.dataset['product'].get('product-name'),
            'description': self.dataset['product'].get('description'),
            'category': self.category
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
        
        
        self.__vendor_options(p)
        self.__product_options(p)
        
        p.save()
        return p
    
    
    def __product_options(self, product):
        """
        Private method that adds, update and maintain vendor product options
        """
        
        vp = VendorProduct.objects.get( product=product, vendor=self.vendor )
        types = dict([(re.sub(r'\W', '', v.name.lower()), v) for v in product.category.option_types.all()])
        
        for variation in self.dataset['product']['variations']:
            options = []
            
            # Create a list of options used for each variation            
            for key in filter(lambda k: k in types.keys(), variation.keys()):
                option, created = Option.objects.get_or_create(option_type=types[key], value=variation[key])
                
                if created:
                    logging.debug('Created option %s', option)
                
                if not product.options.filter(pk=option.pk):
                    logging.debug("Attaching option %s", option)
                    product.options.add(option)
                
                options.append(option)
            
            if len(options) == 0:
                continue
            
            db_variation = None
            
            # FIXME: Sanitise this, and move it out to separate routine
            for v in vp.variations.all():
                # FIXME: Can we rely on this being cached, or is it more efficient
                # to call this outside the loop?
                
                if set(options) - set(v.options.all()):
                    continue
                
                db_variation = v                
                break
            
            else:
                # Create variation
                db_variation = VendorProductVariation.objects.create( vendor_product=vp )
                # FIXME: Pass in when creating variant?
                for o in options:
                    db_variation.options.add(o)
            
                logging.debug('Added availability for combination %s', db_variation)

            in_stock = variation.get('availability')
            
            if in_stock is not None and isinstance(in_stock, bool):
                in_stock = -1 if in_stock else 0
            
            db_variation.in_stock = in_stock
            db_variation.save()

    def __vendor_options(self, product):
        """
        Private method that adds, update and maintain vendor data and options
        for a particular product
        """
        
        
        vp, created = VendorProduct.objects.get_or_create( product=product, vendor=self.vendor )
        
        if created:
            logging.debug('Added product data to vendor: %s', vp)
        
        # FIXME: Map
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
                    # FIXME: Mark this as new and inactive. 
                    # FIXME: Create a workflow ticket for someone to approve the category
                    # and all products related to it
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

    
    @property
    # FIXME: Cache this
    def product_image_path(self):
        """
        Read-only property to retrieve the path to the image for the current
        dataset.
        
        APPAREL_PRODUCT_IMAGE_ROOT/vendor_name/orignal_image
    
        If the image already exists, it will not be downloaded. Returns None if
        no image is specified
        """
        
        try:
           url = self.dataset['product']['image-url'] 
        except KeyError:
            raise IncompleteDataSet('Missing image-url property')
        
        if url is None:
            return None
        
        m = self.re_url.match(url)
        if not m:
            logging.warn('%s does not match %s', url, self.re_url)
            return None
        
        return '%s/%s/%s' % (
            settings.APPAREL_PRODUCT_IMAGE_ROOT, 
            slugify(self.vendor.name), 
            m.group(1)
        )
        
                
    
    def product_image(self):
        """
        Downloads the product image and stores it in the appropriate location. 
        Returns None if no image URL exists in url, otherwise it returns the
        path to the image.
        """
        
        if self.product_image_path is None:
            return None
            
        url = self.dataset['product']['image-url']
        
        
        # FIXME: This ensures that the vendor's directory is present. 
        # Re-implement this when a ProductImageStorage backend has been developed
        # Possibly, move this out
        m = re.match('(.+)/', self.product_image_path)
        d = m.group(1)
        if not os.path.exists(os.path.join(settings.MEDIA_ROOT, d)):
            os.makedirs(os.path.join(settings.MEDIA_ROOT, d))
        
        if not default_storage.exists(self.product_image_path):
            logging.info('Downloading product image %s', url)
            temppath = None
            
            try:
                temppath = fetch(url)
            except HTTPError, e:
                # FIXME: Raise error and roll back
                logging.error('%s (while downloading %s', e, url)
                return
            
            default_storage.save(self.product_image_path, File(open(temppath)))
            logging.debug('Stored image at %s', self.product_image_path)
        else:
            logging.debug('Image %s already exists, will not download', self.product_image_path)
        
        return self.product_image_path


class ImporterException(Exception):
    """
    An exception base class that will prevent the current data to be imported
    and any change to be rolled back.
    However, a client should continue its execution and attempt to import 
    subsequent datasets.
    """
    pass

class SkipProduct(ImporterException):
    """
    Raising this exception indicates that the product should be skipped, but
    this should not be considered an error.
    """
    pass

class IncompleteDataSet(ImporterException):
    """
    The product could not be imported because required data is missing or 
    malformatted.
    """
    pass

