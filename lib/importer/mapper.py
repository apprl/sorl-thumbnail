from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
#from django import settings
from django.core.files.storage import default_storage
from django.core.files import File
from django.template.defaultfilters import slugify
from apps.apparel.models import *
from importer import fetcher
import re
from urllib2 import HTTPError


# FIXME: Move to Django settings directory
PRODUCT_IMAGE_BASE = 'static/product'


class DataMapper():
    
    # Lookups
    
    # Product data fields
    fields = {
        'sku': None,                # Product ID, should be unique with manufacturer
        'product_name': None,       # Product name
        'category_name': None,      # Identifies a category
        'manufacturer_name': None,  # Identifies a manufacturer
        'vendor_name': None,
        'description': None,        # Product description
        'product_image_url': None,  # Product URL
    }
    
    def __init__(self, provider, data={}):
        self.data         = data
        self.category     = None      # Category instance
        self.manufacturer = None      # Manufacturer instance
        self.vendor       = None      # Vendor instance
        self.provider     = provider  # Reference to the provider instance
    
    def translate(self):
        """
        Runs the actual mapping process and does following things (in order)
        
        1) Translates raw data given to the class (in the data property) and 
           stores it as properties.
        
        2) Maps the data to database objects, and create new ones if necessary.
           Following objects are mapped (in order)
           1) Category
           2) Manufacturer
           3) Vendor
           4) Product
        
        3) Adds/Updates product options
        
        4) Adds/Updates vendor options for product
        
        """
        if not isinstance(self.data, dict):
            raise ValueError('data property is expected to be a dictionary')
        
        for attr in self.fields.keys():
            # If there is a set_... method, use it to return the value, otherwise
            
            value = self.data[attr] if attr in self.data else None
            
            if hasattr(self, 'set_%s' % attr):
                value = getattr(self, 'set_%s' % attr)(value)
            
            self.fields[attr] = _trim(value)
            
        # FIXME: Might need to move out to separate routine
        
        self.map_manufacturer()
        self.map_category()
        self.map_vendor()
        self.map_product()
    
    
    def map_manufacturer(self):
        """
        Attempts to locate manufacturer matching the collected. If it can't, a
        new one will be created.
        """
        
        name = self.fields['manufacturer_name']
        
        if not name:
            # FIXME: At this point we've got a problem, and we should probably
            # stop. Best way of stopping is to throw a new kind of exception
            # that the reader listens to. Like ARImporterException
            return
        
        self.manufacturer, created = Manufacturer.objects.get_or_create(name=name)
        
        if created:
            print u"Created new manufacturer: %s" % name
        
        
    # NOTE: This is identical to manufacturer mostly by coincidence. These should
    # be different methods
    def map_category(self):
        """
        Attempts to locate category matching the collected data. If it can't, a
        new one will be created.
        """
        
        name = self.fields['category_name']
        
        if not name or re.match(r'^\s*$', name):
            # FIXME: At this point we've got a problem, and we should probably
            # stop. Best way of stopping is to throw a new kind of exception
            # that the reader listens to. Like ARImporterException
            return
        
        try:
            # NOTE: get_or_create won't work as a case-insensetive match on
            # name is required, and then it will pass the name as 'name__iexact'
            # instead of 'name' to the constructor for category. 
            # I think this is a bug in Django
            self.category = Category.objects.get(key=Category.key_for_name(name))
        
        except ObjectDoesNotExist:
            self.category = Category(
                name=name
            )
            self.category.save()
            print u"Created new category: %s" % name
    
    def map_vendor(self):
        """
        Attempts to locate category matching the collected data. If it can't, a
        new one will be created.        
        """
        
        name = self.fields['vendor_name']
        
        if not name:
            # FIXME: At this point we've got a problem, and we should probably
            # stop. Best way of stopping is to throw a new kind of exception
            # that the reader listens to. Like ARImporterException
            return
        
        self.vendor, created = Vendor.objects.get_or_create(name=name)
        
        if created:
            print u"Created new vendor: %s" % name

        
    def map_product(self):
        """
        Attempts to map the given data to an existing product.
        """
        
        try:
            self.product = Product.objects.get(
                manufacturer__id__exact=self.manufacturer.id,
                sku__exact=self.fields['sku']
            )
        except ObjectDoesNotExist:
            self.product = self.create_product()
            
            # call create object and return
        except MultipleObjectsReturned:
            print u"WARNING: There are more than one product with sku %s for manufacturer %s" % (self.manufacturer.name, self.fields['sku'])
            
            # FIXME: Raise exception that causes this product to be skipped
            return
        else:
            self.update_product()
        
        self.map_product_options()
        self.map_product_image()
        self.map_vendor_options()
        
        # Record that the object was dealt with
    
    def create_product(self):
        """
        Creates a new product with the data collected in 'fields'.
        
        This method is expected to return the newly created product.
        """
        
        product = Product(
            manufacturer=self.manufacturer, 
            product_name=self.fields['product_name'],
            description=self.fields['description'],
            sku=self.fields['sku'],
        )
        
        print u"Created product %s" % product.product_name
        product.save()
        
        if self.category:
            # It is safe to call this method repeatidly
            product.category.add(self.category)
        
        return product
    
    def update_product(self):
        """
        Updates an existing product with the data collected in fields. This
        method is expected to save any changes. Any return value is ignored.
        """
        
        for attr in self.fields.keys():
            if hasattr(self.product, attr):
                setattr(self.product, attr, self.fields[attr])
        
        # FIXME: Is there anyway to see if the object's attributes really has
        # changed since it was loaded? If so, would be good to check it before
        # hitting save, if Django doesn't do that itself
        
        print u"Updated product %s" % self.product.product_name
        self.product.save()
        
    def map_vendor_options(self):
        """
        Updates, or adds, product vendor options, for example price and currency.
        
        This is done by calling 'set_vendor_option_...' method on self, or finding the
        value in data
        """
        
        if not self.vendor:
            print "No vendor to update"
            return
        
        opt, created = VendorProduct.objects.get_or_create(product=self.product,
                                                           vendor=self.vendor)
        
        if created:
            print u'Added product data to vendor: %s' % opt
        
        # FIXME: Make this better
        
        fields = filter(
                    lambda x: x not in ['vendor_id', 'product_id', 'id'],
                    map(
                        lambda f: f.attname,
                        opt._meta.fields
                    )
                )
        
        for field in fields:
            value = None
            
            if hasattr(self, 'set_vendor_option_%s' % field):
                value = getattr(self, 'set_vendor_option_%s' % field)()
            elif field in self.data:
                value = self.data[field]
            else:
                print u'No mapping for vendor option %s' % field
                value = None
                continue
            
            if value == '':
                # Ensure correct NULL handling
                value = None
            
            # FIXME: Wrap in debug statement
            print u"Set vendor options %s to %s" % (field, value)
            
            
            setattr(opt, field, value)
        
        opt.save()
    
    def map_product_options(self):
        """
        Updates, or adds options for the product. This method doesn't remove
        any options.
        
        This is done by calling 'set_option_...' method on self, or finding the
        value in data
        """
        
        # 1 Get a list of option types from categories
        # FIXME: Retrieve these objects in only one query
        
        for category in self.product.category.all():
            for option_type in category.option_types.all():
                key = re.sub(r'\W', '', option_type.name.lower())
                
                # 2 Collect raw data by calling set_[typename], or use field in self.data
                
                value = None
                
                if hasattr(self, 'set_option_%s' % key):
                    value = getattr(self, 'set_option_%s' % key)()
                elif key in self.data:
                    value = self.data[key]
                else:
                    print u'No mapping for option type %s' % key
                
                if not value:
                    continue
                
                value = _trim(value)
                
                # FIXME: One could move this code to the Option or Product class                
                opt, created = Option.objects.get_or_create(option_type=option_type, value=value)
                
                if created:
                    print u"Created option '%s: %s'" % (option_type.name, value)
                
                if not self.product.options.filter(pk=opt.pk):
                    print u"Attaching option '%s: %s'" % (option_type.name, value)
                    self.product.options.add(opt)
    
    def map_product_image(self):
        """
        Fetches the file specified in 'product_image' and assigns it to the 
        product 
        """
        if not 'product_image_url' in self.fields or not self.fields['product_image_url']:
            return
        
        (url, name) = re.match(r'^.+/(.+)$', self.fields['product_image_url']).group(0,1)
        
        sitepath = '%s/%s_%s' % (PRODUCT_IMAGE_BASE, self.provider.name, name)
        
        if not default_storage.exists(sitepath):
            print u"Downloading product image %s" % url
            temppath = None
            
            try:
                temppath = fetcher.fetch(url)
            except HTTPError, e:
                # FIXME: Replace with proper logging
                print u"%s: (while downloading %s)" % (e, url)
                return
            
            default_storage.save(sitepath, File(open(temppath)))
            
        self.product.product_image = sitepath
        self.product.save()
            
        # FIXME: Delete file at temppath? Can it be done implictly when the process
        # exists?
        
        
        
def _trim(value):
    if value:
        return re.sub(r'^\s*|\s*$', '', value)
    
    return value
