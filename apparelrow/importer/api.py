import logging
import re
import os
import os.path
import subprocess
from urllib2 import HTTPError, URLError
import decimal
import time

import requests
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files import storage
from django.core.files.base import ContentFile
from django.template.defaultfilters import slugify
from django.db import transaction
from django.db import IntegrityError
from django.db.models import Count
from django.conf import settings
from django.db.models.loading import get_model
from django.utils.encoding import smart_str
from django.utils.http import urlquote

from apparelrow.importer.framework.fetcher import fetch

try:
    from MySQLdb import MySQLError as DBError
except ImportError:
    class DBError(Exception):
        pass

logger = logging.getLogger('apparel.importer.api')
image_logger = logging.getLogger('apparel.importer.api.image')

GENDERS = ['M', 'W', 'U']

"""
Provides an API for importing and setting up product data for the Apparelrow
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
        'discount-price': 1299.00,
        'currency': 'SEK',
        'delivery-cost': 99.00,
        'delivery-time': '3-5 D',
        'availability': True OR a number (0 for not available),
        'product-url': 'http://caliroots.com/system/search/product_vert.asp?id=20724',
        'image-url': [
            ('http://caliroots.com/data/product/images/20724200911114162028734214_XL.jpg', 10000),
            ('http://caliroots.com/data/product/images/23144363545435345345346434_L.jpg', 1000)
        ]
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
    _fxrates = None

    def __init__(self, dataset=None, import_log=None):
        self.version          = "0.1"
        self.product          = None
        self._dataset         = dataset
        self._import_log      = import_log
        self._vendor_product  = None
        self._vendor_category = None
        self._vendor_brand    = None
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

            logger.debug('ID [%s]  Name [%s] Brand [%s]  ' % (
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
            'manufacturer': self.manufacturer,
            'static_brand': self.dataset['product']['manufacturer'],
            'gender': self.dataset['product']['gender'],
            'feed_gender': self.dataset['product']['gender'],
            'availability': False if self.dataset['product']['availability'] == 0 else True
        }

        try:
            self.product = get_model('apparel', 'Product').objects.get(
                static_brand=self.dataset['product']['manufacturer'],
                sku__exact=self.dataset['product']['product-id']
            )
            logger.debug('Found existing product: [id %s] %s' % (self.product.id, self.product))
        except ObjectDoesNotExist:
            fields['product_image'] = self.product_image
            self.product = get_model('apparel', 'Product').objects.create(
                sku=self.dataset['product']['product-id'],
                **fields
            )
            logger.debug('Created new product: [id %s] %s' % (self.product.id, self.product))

        except MultipleObjectsReturned:
            raise SkipProduct('Multiple products found with sku %s for unmapped (static) vendor brand %s' % (self.fields['sku'], self.fields['static_brand']))

        else:
            # Update product
            for f in fields:
                # If category, gender or manufactueer is set on product and the
                # previous imported value is None we will not try to override
                # it. Should fix problems with 404 products.
                if f == 'category':
                    if self.product.category and not fields.get(f):
                        continue
                elif f == 'gender':
                    if self.product.gender and not fields.get(f):
                        continue
                elif f == 'manufacturer':
                    if self.product.manufacturer and not fields.get(f):
                        continue

                setattr(self.product, f, fields.get(f))

        self.__vendor_options()
        self.__product_options()

        # If stored product image path is not the same as imported product
        # image path try to download it again
        if self.product.product_image != self._get_first_product_image_path():
            self.product.product_image = self.product_image

        self.product.save()

        return self.product

    def __product_options(self):
        """
        Private method that adds, update and maintain vendor product options
        """
        vp = get_model('apparel', 'VendorProduct').objects.get( product=self.product, vendor=self.vendor )
        types = dict([(re.sub(r'\W', '', v.name.lower()), v) for v in get_model('apparel', 'OptionType').objects.all()])

        if 'pattern' in types.keys():
            for pattern in self.dataset['product']['patterns']:
                if pattern:
                    option, created = get_model('apparel', 'Option').objects.get_or_create(option_type=types['pattern'], value=pattern)

                    if created:
                        logger.debug('Created option %s' % option)

                    if not self.product.options.filter(pk=option.pk):
                        logger.debug("Attaching option %s" % option)
                        self.product.options.add(option)

        for variation in self.dataset['product']['variations']:
            options = []

            # Create a list of options used for each variation
            for key in filter(lambda k: k in types.keys(), variation.keys()):
                if variation[key]:
                    option, created = get_model('apparel', 'Option').objects.get_or_create(option_type=types[key], value=variation[key])

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
                db_variation = get_model('apparel', 'VendorProductVariation').objects.create( vendor_product=vp )
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
            self._vendor_product, created = get_model('apparel', 'VendorProduct').objects.get_or_create(
                product=self.product,
                vendor=self.vendor,
            )

            self._vendor_product.vendor_category = self.vendor_category
            self._vendor_product.vendor_brand = self.vendor_brand
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

        # No discount price is mapped but we can get it from the stored original price
        if self.vendorproduct.original_price and not self.dataset['product']['discount-price'] and self.vendorproduct.original_currency == self.dataset['product']['currency']:
            price_decimal = decimal.Decimal(self.dataset['product']['price'])
            if price_decimal > decimal.Decimal('0.0') and  self.vendorproduct.original_price > (price_decimal * decimal.Decimal('1.1')):
                self.dataset['product']['discount-price'] = self.dataset['product']['price']
                self.dataset['product']['price'] = str(self.vendorproduct.original_price)

        # Make sure that discount-price is None
        if not self.dataset['product']['discount-price']:
            self.dataset['product']['discount-price'] = None

        fields = {
            'buy_url': self.dataset['product']['product-url'],
            'original_price': self.dataset['product']['price'] or '0.0',
            'original_currency': self.dataset['product']['currency'],
            'original_discount_price': self.dataset['product']['discount-price'],
            'original_discount_currency': self.dataset['product']['currency'],
            'availability': self.availability
        }

        # TODO: we should remove this, we do the currency exchange during
        # presentation
        rates = self.fxrates()
        if len(rates.keys()) > 0:
            fields['currency'] = settings.APPAREL_BASE_CURRENCY

            if settings.APPAREL_BASE_CURRENCY == fields['original_currency']:
                fields['price'] = fields['original_price']
                logger.debug('Setting price to %s %s', fields['original_price'], fields['original_currency'])
                if fields['original_discount_price']:
                    fields['discount_price'] = fields['original_discount_price']
                    fields['discount_currency'] = fields['original_currency']
                    logger.debug('Setting discount price to %s %s', fields['original_discount_price'], fields['original_currency'])
                else:
                    fields['discount_price'] = None
                    fields['discount_currency'] = None
            elif fields['original_currency'] in rates:
                try:
                    fields['price'] = rates[fields['original_currency']].convert(float(fields['original_price']))
                    logger.debug('Setting price to %s %s (= %f %s)', fields['original_price'], fields['original_currency'], fields['price'], fields['currency'])

                    if fields['original_discount_price']:
                        fields['discount_price'] = rates[fields['original_currency']].convert(float(fields['original_discount_price']))
                        fields['discount_currency'] = fields['currency']
                        logger.debug('Setting discount price to %s %s (= %f %s)', fields['original_discount_price'], fields['original_currency'], fields['discount_price'], fields['currency'])
                    else:
                        fields['discount_price'] = None
                        fields['discount_curency'] = None
                except TypeError:
                    raise SkipProduct('Could not convert currency to base currency')
            else:
                self._import_log.messages.create(
                    status='attention',
                    message='Missing exchange rate for %s. Add and run the arfxrates --update command' % fields['original_currency'],
                )

        for f in fields:
            setattr(self.vendorproduct, f, fields[f])

        self.vendorproduct.save()

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
                'price', 'discount-price', 'currency', 'delivery-cost', 'delivery-time', 'availability',
                'product-url', 'image-url', 'description', 'variations')
            ]

        except KeyError, key:
            raise IncompleteDataSet(key)

        # Check that we support this version
        if self.dataset['version'] != self.version:
            raise ImporterError('Incompatable version number "%s" (this is version %s)', self.dataset.get('version'), self.version)

        # Check for empty manufacturer
        if not self.dataset['product']['manufacturer']:
            raise IncompleteDataSet('manufacturer', 'The field manufacturer cannot be empty or null')

        # Check that the gender field is valid (it may be None)
        if self.dataset['product']['gender'] is not None:
            if self.dataset['product']['gender'] not in GENDERS:
                raise IncompleteDataSet('gender', '%s is not a recognised gender' % key)

        # Make sure the image-url is a list
        if not isinstance(self.dataset['product']['image-url'], list):
            raise IncompleteDataSet('image-url', 'The field image-url must be a list, not %s' % (type(self.dataset['product']['image-url']),))

        # Check for empty image-url
        image_url_empty = True
        for image_url in self.dataset['product']['image-url']:
            if image_url[0]:
                image_url_empty = False
                break

        if image_url_empty:
            raise IncompleteDataSet('image-url', 'The field image-url contains an empty list')

        # Make sure the variations is a list
        if not isinstance(self.dataset['product']['variations'], list):
            raise IncompleteDataSet('variations', 'The field variations must be a list, not %s' % (type(self.dataset['product']['variations']),))

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
        to manually defined one Apparelrow.
        """

        if not self._vendor_category:
            category_names = self.dataset['product']['category']

            # Force string
            if isinstance(category_names, list):
                category_names = ' '.join(category_names)

            self._vendor_category, created = get_model('apparel', 'VendorCategory').objects.get_or_create(vendor=self.vendor, name=category_names)

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
    def vendor_brand(self):
        """
        Returns the VendorBrand instance that maps the extracted brand to a
        manually defined one by Apprl. If a Brand exists with the same name an
        automatic mapping will occur.
        """
        if not self._vendor_brand:
            name = self.dataset['product']['manufacturer']
            self._vendor_brand, created = get_model('apparel', 'VendorBrand').objects.get_or_create(vendor=self.vendor, name=name)
            if created:
                self._import_log.messages.create(
                    status='attention',
                    message='New VendorBrand: %s, add mapping to Brand to update related products' % (self._vendor_brand,)
                )
                logger.debug('Created new vendor brand [id: %s] %s' % (self._vendor_brand.id, self._vendor_brand))
            else:
                logger.debug('Using vendor brand [id: %s] %s' % (self._vendor_brand.id, self._vendor_brand))

            if self._vendor_brand.brand is None:
                brand_model = get_model('apparel', 'Brand')
                try:
                    brand = get_model('apparel', 'Brand').objects.get(name__iexact=name)
                    self._vendor_brand.brand = brand
                    self._vendor_brand.save()
                    logger.debug('Direct mapping from VendorBrand %s to Brand %s' % (self._vendor_brand, brand))
                except brand_model.DoesNotExist:
                    logger.debug('Direct mapping from VendorBrand %s is not possible' % (self._vendor_brand,))

        return self._vendor_brand

    @property
    def manufacturer(self):
        """
        Returns the mapped brand for the product. This may return None.
        """
        return self.vendor_brand.brand

    @property
    def availability(self):
        availability = self.dataset['product']['availability']
        if availability == 0:
            logger.debug('Adding availability to product: Out of stock')
            return 0

        elif availability:
            if availability < 0:
                logger.debug('Adding availability to product: In stock')
            else:
                logger.debug('Adding availability to product: %i in stock' % (availability,))
            return availability

        logger.debug('Adding availability to product: No information available')
        return None

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

            self._vendor, created = get_model('apparel', 'Vendor').objects.get_or_create(name=name)

            if created:
                logger.debug('Created new vendor [id: %s] %s' % (self._vendor.id, self._vendor))
            else:
                logger.debug('Using vendor [id: %s] %s' % (self._vendor.id, self._vendor))

        return self._vendor

    def _product_image_path(self, url):
        """
        Returns the local path for the given URL.

        APPAREL_PRODUCT_IMAGE_ROOT/vendor_name/image_number__product_id__orignal_image_filename
        """
        try:
            root, ext = os.path.splitext(url)
        except TypeError, AttributeError:
            raise IncompleteDataSet('image-url', '[%s] is not a string' % (smart_str(url),))

        ext = ext.split('?', 1)[0]
        brand_name = self.manufacturer or self.dataset['product']['manufacturer']

        return '%s/%s/%s/%s__%s%s' % (
            settings.APPAREL_PRODUCT_IMAGE_ROOT,
            slugify(self.vendor.name),
            slugify(brand_name),
            slugify(self.dataset['product']['product-name']),
            slugify(self.dataset['product']['product-id']),
            urlquote(ext)
        )

    def _download_product_image(self, product_image, url, min_content_length):
        """
        Download product image.

        Check for valid content_length and content_type.
        """
        if not (storage.default_storage.exists(product_image) and storage.default_storage.size(product_image) > min_content_length):
            try:
                request_handler = requests.get(url, timeout=10)
                request_handler.raise_for_status()
            except (requests.exceptions.RequestException, URLError, HTTPError, ValueError), e:
                image_logger.error(u'Download failed [%s]: %s' % (url, e))
                return False

            content_length = int(request_handler.headers.get('content-length', 0))
            content_type = request_handler.headers.get('content-type', '')
            if content_length < min_content_length or content_type.find('image') == -1:
                image_logger.error(u'Invalid content [%s] [L: %s] [T: %s]' % (url, content_length, content_type))
                return False

            image_logger.debug(u'Image data [R: %s] [L: %s] [T: %s]' % (request_handler.status_code, content_length, content_type))

            storage.default_storage.save(product_image, ContentFile(request_handler.content))

        return True

    def _get_first_product_image_path(self):
        for url, content_length in self.dataset['product']['image-url']:
            return self._product_image_path(url)

    @property
    def product_image(self):
        """
        Downloads the product image and stores it in the appropriate location.
        Returns the relative path to the stored image.
        """
        if not self._product_image:
            directory = os.path.join(settings.MEDIA_ROOT,
                                     settings.APPAREL_PRODUCT_IMAGE_ROOT,
                                     slugify(self.vendor.name))

            if not os.path.exists(directory):
                os.makedirs(directory)

            for url, content_length in self.dataset['product']['image-url']:
                image_logger.debug(u'Downloading image [%s]' % (url,))
                self._product_image = self._product_image_path(url)
                if self._download_product_image(self._product_image, url, content_length):
                    image_logger.debug(u'Saved image [%s]' % (self._product_image,))
                    return self._product_image

            raise SkipProduct('Could not download product image')

        return self._product_image

    def fxrates(self):
        if not API._fxrates:
            if hasattr(settings, 'APPAREL_BASE_CURRENCY'):
                API._fxrates = dict([(c.currency, c) for c in get_model('importer', 'FXRate').objects.filter(base_currency=settings.APPAREL_BASE_CURRENCY)])
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
            return 'Missing field %s (%s)' % (self.field, self.msg)

        return '[No reason given]' if self.msg is None else self.msg
