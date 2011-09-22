import logging
import re
import os
import subprocess
from urllib2 import HTTPError, URLError

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files import storage, File
from django.template.defaultfilters import slugify
from django.db import transaction
from django.db import IntegrityError
from django.db.models import Count
from django.conf import settings

from apparel.models import *
from importer.framework.fetcher import fetch

try:
    from MySQLdb import MySQLError as DBError
except ImportError:
    class DBError(Exception):
        pass


logger = logging.getLogger('apparel.importer.api')


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
        'category': 'Sneakers',
        'manufacturer': 'Jordan',
        'price': 1399.00,
        'currency': 'SEK',
        'delivery-cost': 99.00,
        'delivery-time': '3-5 D',
        'availability': True OR a number (0 for not available),
        'product-url': 'http://caliroots.com/system/search/product_vert.asp?id=20724',
        'image-url': 'http://caliroots.com/data/product/images/20724200911114162028734214_L.jpg',
        'description': 'Classic Flight 45',
        'gender': 'F',
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
    re_url   = re.compile(r'^.+/(.+)$')
    _fxrates = None
    
        
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
        
        logger.debug('****** About to import dataset ******')
        p = None
        
        try:
            if data:
                self.dataset = data
            
            self.validate()

            logger.debug('ID [%s]  Name [%s] Manufacturer [%s]  ' % (
                self.dataset['product']['product-id'].encode('utf8'),
                self.dataset['product']['product-name'].encode('utf8'),
                self.dataset['product']['manufacturer'].encode('utf8')
            ))
            
            self.import_product()
        except ImporterError, e:
            logger.error(u'Record skipped: %s' % e)
            raise
        except DBError, e:
            logger.debug(u'Cought exception from database driver: %s' % e)
            raise ImporterError('Could not insert product: %s' % e)
        
        logger.info('Imported %s' % self.product)
        
        return self.product
    
    
    def import_product(self):
        """
        Imports the product
        """
        
        # Download and store product image 
        fields = {
            'product_name': self.dataset['product']['product-name'],
            'description': self.dataset['product']['description'],
            'category': self.category,
            'product_image': self.product_image,
            'gender': self.dataset['product']['gender'],
            'feed_gender': self.dataset['product']['gender']
        }
        
        try:
            self.product = Product.objects.get(
                manufacturer__id__exact=self.manufacturer.id,
                sku__exact=self.dataset['product']['product-id']
            )
            logger.debug('Found existing product: [id %s] %s' % (self.product.id, self.product))
        except ObjectDoesNotExist:
            self.product = Product.objects.create(
                manufacturer=self.manufacturer, 
                sku=self.dataset['product']['product-id'],
                **fields
            )
            logger.debug('Created new product: [id %s] %s' % (self.product.id, self.product))
        
        except MultipleObjectsReturned:
            raise SkipRecord('Multiple products found with sku %s for manufacturer %s' % (self.manufacturer.name, self.fields['sku']))
            
        else:
            # Update product
            for f in fields:
                setattr(self.product, f, fields.get(f))
        
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
        
        for variation in self.dataset['product']['variations']:
            options = []
            
            # Create a list of options used for each variation
            for key in filter(lambda k: k in types.keys(), variation.keys()):
                option, created = Option.objects.get_or_create(option_type=types[key], value=variation[key])
                
                if created:
                    logger.debug('Created option %s' % option)
                
                if not self.product.options.filter(pk=option.pk):
                    logger.debug("Attaching option %s" % option)
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
            
                logger.debug('Added availability for combination %s', db_variation)

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
                logger.debug('Added product data to vendor: %s', self._vendor_product)

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
            'buy_url': self.dataset['product']['product-url'],
            'original_price': self.dataset['product']['price'],
            'original_currency': self.dataset['product']['currency'],
            'availability': self.availability
        }
        
        rates = self.fxrates()
        
        if len(rates.keys()) > 0:
            fields['currency'] = settings.APPAREL_BASE_CURRENCY
            
            if settings.APPAREL_BASE_CURRENCY == fields['original_currency']:
                fields['price'] = fields['original_price']
            
            elif fields['original_currency'] in rates:
                fields['price'] = rates[fields['original_currency']].convert(float(fields['original_price']))
                logger.debug('Setting price to %s %s (= %f %s)', fields['original_price'], fields['original_currency'], fields['price'], fields['currency'])
            else:
                self._import_log.messages.create(
                    status='attention',
                    message='Missing exchange rate for %s. Add and run the arfxrates --update command' % fields['original_currency'],
                )
        
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
            raise IncompleteDataSet('image-url', 'url [%s] is not a string' % url)

        if not m:
            raise IncompleteDataSet('image-url', 'product image URL [%s] does not match [%s]' % (url, self.re_url))

        filename = m.group(1)
        #filename_temp, extension = os.path.splitext(filename)
        # FIXME: Here we want to find the mimetype and use that instead of just 'jpg', this is not possible:
        #   * Here we set the path for where to save the downloaded file later, which means that we need to download the file here, everytime to check mimetype
        #   * The builtin python mimetypes module does not work, python-magic works but is incompatible with the version of sorl-thumbnail we uses
        #if not extension:
            #filename = '%s.%s' % (filename_temp, 'jpg')

        return '%s/%s/%s.%s' % (
            settings.APPAREL_PRODUCT_IMAGE_ROOT, 
            slugify(self.vendor.name),
            self.dataset['product']['product-id'],
            filename
        )
        
    
    def validate(self):
        """
        Validates a data structure. Returns True on success, will otherwise throw
        an exception
        """
        
        # Check that dataset contains all required keys
        try:
            [self.dataset[f] for f in ('version', 'date', 'vendor', 'product',)]
            [self.dataset['product'][f] for f in (
                'product-id', 'product-name', 'category', 'manufacturer', 'gender',
                'price', 'currency', 'delivery-cost', 'delivery-time', 'availability',
                'product-url', 'image-url', 'description', 'variations')
            ]
        
        except KeyError, key:
            raise IncompleteDataSet(key)
        
        # Check that we support this version
        if self.dataset['version'] != self.version:
            raise ImporterError('Incompatable version number "%s" (this is version %s)', self.dataset.get('version'), self.version)
        
        # Check that the gender field is valid (it may be None)
        if self.dataset['product']['gender'] is not None:
            try:
                dict(PRODUCT_GENDERS)[self.dataset['product']['gender']]
            except KeyError, key:
                raise IncompleteDataSet('gender', '%s is not a recognised gender' % key)
        
        # Make sure the variations is a list
        if not isinstance(self.dataset['product']['variations'], list):
            raise IncompleteDataSet('variations', 'Variations must be a list, not %s' % type(self.dataset['product']['variations']))
        
        logger.debug('Dataset is valid')
        return True
    
    @property
    def dataset(self):
        """
        The API's dataset. Required before calling import() or accessing any
        data property.
        """
        if not self._dataset:
            raise IncompleteDataSet(None, 'No dataset')
        
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
            category_names = self.dataset['product']['category']
                        
            # Force string
            if isinstance(category_names, list):
                category_names = ' '.join(category_names)

            @transaction.commit_on_success
            def vendor_category_get_or_create(vendor, category):
                created = True
                try:
                    obj = VendorCategory.objects.create(vendor=vendor, name=category)
                except IntegrityError:
                    transaction.commit()
                    created = False
                    obj = VendorCategory.objects.get(vendor=vendor, name=category)
                return obj, created

            self._vendor_category, created = vendor_category_get_or_create(self.vendor, category_names)
            #self._vendor_category, created = VendorCategory.objects.get_or_create(vendor=self.vendor, name=category_names)

            if created:
                self._import_log.messages.create(
                    status='attention',
                    message='New VendorCategory: %s, add mapping to Category to update related products' % self._vendor_category,
                )
                logger.debug('Creating new vendor category: %s' % category_names)

        return self._vendor_category
    
    @property
    def category(self):
        """
        Returns the mapped category for the product. This may return None
        """
        return self.vendor_category.category

    @property
    def availability(self):
        availability = self.dataset['product']['availability']
        if availability:
            if availability == 0:
                logger.debug('Adding availability to product: Out of stock')
            elif availability < 0:
                logger.debug('Adding availability to product: In stock')
            else:
                logger.debug('Adding availability to product: %i in stock' % (availability,))
            return availability

        logger.debug('Adding availability to product: No information available')
        return None
            
    @property 
    def manufacturer(self):
        """
        Retrieves, or creates, the product's manufacturer.
        """
        
        if not self._manufacturer:
            name = self.dataset['product']['manufacturer']
            
            self._manufacturer, created = Manufacturer.objects.get_or_create(name=name)
            
            if created: 
                logger.debug('Created new manufacturer [id: %s] %s' % (self._manufacturer.id, self._manufacturer))
            else:
                logger.debug('Using manufacturer [id: %s] %s' % (self._manufacturer.id, self._manufacturer))
        
        return self._manufacturer
    
    @property
    def vendor(self):
        """
        Retrives, or creates, the vendor of this dataset
        """
        
        if not self._vendor:
            try:
                name = self.dataset['vendor']
            except KeyError, key:
                raise IncompleteDataSet(key)
            
            self._vendor, created = Vendor.objects.get_or_create(name=name)
            
            if created: 
                logger.debug('Created new vendor [id: %s] %s' % (self._vendor.id, self._vendor))
            else:
                logger.debug('Using vendor [id: %s] %s' % (self._vendor.id, self._vendor))
        
        return self._vendor

    
    @property
    def product_image(self):
        """
        Downloads the product image and stores it in the appropriate location. 
        Returns the relative path to the stored image.
        """
        
        if not self._product_image:        
            url = self.dataset['product']['image-url']
            
            # FIXME: This ensures that the vendor's directory is present. 
            # Re-implement this when a ProductImageStorage backend has been developed
            # Possibly, move this out
            self._product_image = self.product_image_path(url)
            m = re.match('(.+)/', self._product_image)
            d = m.group(1)
            
            if not os.path.exists(os.path.join(settings.MEDIA_ROOT, d)):
                os.makedirs(os.path.join(settings.MEDIA_ROOT, d))
            
            if not storage.default_storage.exists(self._product_image):
                logger.debug(u'Downloading product image %s' % url)
                temppath = None
                
                try:
                    temppath = fetch(url)
                except (URLError, HTTPError), e:
                    # FIXME: We could have a re-try loop for certain errors
                    # FIXME: We could create the product, and mark it as unpublished
                    #        until the image has been added
                    logger.error(u'%s (while downloading %s)' % (e, url))
                    raise SkipProduct('Could not download product image')

                if re.search(r':.* text', subprocess.Popen(["file", '-L', temppath], stdout=subprocess.PIPE).stdout.read()):
                    logger.error(u'No image found, only text (while downloading %s)' % (url,))
                    raise SkipProduct('Could not download product image')

                storage.default_storage.save(self._product_image, File(open(temppath)))
                logger.debug(u'Stored image at %s' % self._product_image)
            else:
                logger.debug(u'Image already exists, will not download [%s]' % self._product_image)
        
        return self._product_image
    
        
    def fxrates(self):
        from importer.models import FXRate
        
        if not API._fxrates:
            if hasattr(settings, 'APPAREL_BASE_CURRENCY'):
                API._fxrates = dict([(c.currency, c) for c in FXRate.objects.filter(base_currency=settings.APPAREL_BASE_CURRENCY)])
            else:
                logger.warning('Missing APPAREL_BASE_CURRENCY setting, prices will not be converted')
                API._fxrates = {}
        
        return API._fxrates


class ImporterError(Exception):
    """
    An exception base class that will prevent the current data to be imported
    and any change to be rolled back.
    However, a client should continue its execution and attempt to import 
    subsequent datasets.
    """
    def __unicode__(self):
        return unicode(self.__str__(), 'utf-8')

class SkipProduct(ImporterError):
    """
    Raising this exception indicates that the product should be skipped, but
    this should not be considered an error.
    """
    pass

class IncompleteDataSet(ImporterError):
    """
    The product could not be imported because required data is missing or 
    malformatted.
    """
    def __init__(self, field=None, msg=None):
        self.field = field
        self.msg   = msg
        
        return super(IncompleteDataSet, self).__init__()
    
    def __str__(self):
        if self.field:
            return 'Missing field %s' % self.field
    
        return '[No reason given]' if self.msg is None else self.msg
