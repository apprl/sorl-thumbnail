import logging, re, tempfile, urllib2, os

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files import storage, File
from django.template.defaultfilters import slugify
from django.db import transaction
from django.db.models import Count
from django.conf import settings
from urllib2 import HTTPError, URLError

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
    
    def __init__(self, dataset=None, import_log=None):
        self.version          = "0.1"
        self.product          = None
        self._dataset         = dataset
        self._import_log      = import_log
        self._vendor_product  = None
        self._vendor_category = None
        self._manufacturer    = None
        self._vendor          = None
        self._product_image   = None
            
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
            self.import_product()
        
        except ImporterException, e:
            # Log ImporterException
            logging.error(u'%s, record skipped', e)
            raise
        except Exception, e:
            raise
        else:
            logging.info(u'Imported %s', self.product)
            return self.product
    
    
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
            self.product = Product.objects.get(
                manufacturer__id__exact=self.manufacturer.id,
                sku__exact=self.dataset['product']['product-id']
            )
        except ObjectDoesNotExist:
            self.product = Product.objects.create(
                manufacturer=self.manufacturer, 
                sku=self.dataset['product']['product-id'],
                product_image=self.product_image,
                **fields
            )

            logging.debug('Created new product')
        
        except MultipleObjectsReturned:
            s = u'There are more than one product with sku %s for manufacturer %s' % (self.manufacturer.name, self.fields['sku'])
            logging.error(s)
            raise SkipRecord(s)
        else:
            # Update product
            for f in fields:
                setattr(self.product, f, fields.get(f))
            
            # FIXME: How do we deal with category? Re-assign?
            logging.debug('Updated product')
        
        self.__vendor_options()
        self.__product_options()
        
        self.product.save()
        return self.product
    
    
    def __product_options(self):
        """
        Private method that adds, update and maintain vendor product options
        """
        
        vp = VendorProduct.objects.get( product=self.product, vendor=self.vendor )
        types = dict([(re.sub(r'\W', '', v.name.lower()), v) for v in OptionType.objects.all()])
        
        try:
            self.dataset['product']['variations']
        except KeyError, e:
            raise IncompleteDataSet('Missing variations')
        
        for variation in self.dataset['product']['variations']:
            options = []
            
            # Create a list of options used for each variation
            for key in filter(lambda k: k in types.keys(), variation.keys()):
                option, created = Option.objects.get_or_create(option_type=types[key], value=variation[key])
                
                if created:
                    logging.debug(u'Created option %s', option)
                
                if not self.product.options.filter(pk=option.pk):
                    logging.debug(u"Attaching option %s", option)
                    self.product.options.add(option)
                
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
            
                logging.debug(u'Added availability for combination %s', db_variation)

            in_stock = variation.get('availability')
            
            if in_stock is not None and isinstance(in_stock, bool):
                in_stock = -1 if in_stock else 0
            
            db_variation.in_stock = in_stock
            db_variation.save()

    @property
    def vendorproduct(self):
        if not self._vendor_product:
            self._vendor_product, created = VendorProduct.objects.get_or_create( 
                product=self.product, 
                vendor=self.vendor,
            )
            
            if created:
                self._vendor_product.vendor_category = self.vendor_category
                self._vendor_product.save()
                logging.debug(u'Added product data to vendor: %s', self._vendor_product)

        return self._vendor_product
        

    def __vendor_options(self):
        """
        Private method that adds, update and maintain vendor data and options
        for a particular product
        """
        
        # FIXME: Map
        #   - delivery time
        #   - delivery cost (Property of vendor?)
        
        fields = {
            'buy_url': self.dataset['product'].get('product-url'),
            'price': self.dataset['product'].get('price'),
            'currency': self.dataset['product'].get('currency'),            
        }
        
        for f in fields:
            setattr(self.vendorproduct, f, fields[f])
        
        self.vendorproduct.save()

    def product_image_path(self, url):
        """
        Returns the local path for the given URL.
        
        APPAREL_PRODUCT_IMAGE_ROOT/vendor_name/orignal_image
    
        If the image already exists, it will not be downloaded. Returns None if
        no image is specified
        """
        
        try:
            m = self.re_url.match(url)
        except TypeError:
            raise IncompleteDataSet('url [%s] is not a string', url)

        if not m:
            raise IncompleteDataSet('product image URL [%s] does not match [%s]', url, self.re_url)
        
        return '%s/%s/%s' % (
            settings.APPAREL_PRODUCT_IMAGE_ROOT, 
            slugify(self.vendor.name),
            m.group(1)
        )
        
    
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
    def vendor_category(self):
        """
        Returns the VendorCategory instance that maps the extracted category
        to manually defined one ApparelRow.
        """
        
        if not self._vendor_category:
            try:
                category_names = self.dataset['product']['categories']
            except KeyError, e:
                raise IncompleteDataSet('No category')
            
            # Force string
            if isinstance(category_names, list):
                category_names = ' '.join(category_names)
            
            self._vendor_category, created = VendorCategory.objects.get_or_create(vendor=self.vendor, name=category_names)

            if created:
                self._import_log.messages.create(
                    status='attention',
                    message='New VendorCategory: %s, add mapping to Category to update related products' % self._vendor_category,
                )
                logging.debug('Creating new vendor category: %s', category_names)

        return self._vendor_category
    
    @property
    def category(self):
        """
        Returns the mapped category for the product. This may return None
        """
        return self.vendor_category.category
            
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
    def product_image(self):
        """
        Downloads the product image and stores it in the appropriate location. 
        Returns the relative path to the stored image.
        """
        
        if not self._product_image:        
            try:
                url = self.dataset['product']['image-url']
            except KeyError, e:
                raise IncompleteDataSet('Missing image-url property')
            
            # FIXME: This ensures that the vendor's directory is present. 
            # Re-implement this when a ProductImageStorage backend has been developed
            # Possibly, move this out
            self._product_image = self.product_image_path(url)
            m = re.match('(.+)/', self._product_image)
            d = m.group(1)
            
            if not os.path.exists(os.path.join(settings.MEDIA_ROOT, d)):
                os.makedirs(os.path.join(settings.MEDIA_ROOT, d))
            
            if not storage.default_storage.exists(self._product_image):
                logging.info('Downloading product image %s', url)
                temppath = None
                
                try:
                    temppath = fetch(url)
                except (URLError, HTTPError), e:
                    # FIXME: We could have a re-try loop for certain errors
                    # FIXME: We could create the product, and mark it as unpublished
                    #        until the image has been added
                    logging.error('%s (while downloading %s)', e, url)
                    raise SkipProduct('Could not download product image')
                                
                storage.default_storage.save(self._product_image, File(open(temppath)))
                logging.debug('Stored image at %s', self._product_image)
            else:
                logging.debug('Image %s already exists, will not download', self._product_image)
        
        return self._product_image

class ImporterException(Exception):
    """
    An exception base class that will prevent the current data to be imported
    and any change to be rolled back.
    However, a client should continue its execution and attempt to import 
    subsequent datasets.
    """
    def __unicode__(self):
        return unicode(self.__str__(), 'utf-8')

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

