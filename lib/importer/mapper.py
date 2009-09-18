from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
#from django import settings
from django.core.files.storage import default_storage
from django.core.files import File
from apps.apparel.models import *
from importer import fetcher
import re


# FIXME: Move to Django settings directory
PRODUCT_IMAGE_BASE = 'static/product'


class DataMapper():
    
    # Lookups
    category          = None      # Category instance
    manufacturer      = None      # Manufacturer instance
    
    # Product data fields
    fields = {
        'vendor_name': None,        # Name of vendor
        'sku': None,                # Product ID, should be unique with manufacturer
        'product_name': None,       # Product name
        'category_name': None,      # Identifies a category
        'manufacturer_name': None,  # Identifies a manufacturer
        'description': None,        # Product description
        'product_image_url': None,  # Product URL
    }
    
    def __init__(self, data={}):
        self.data     = data
    
    def translate(self):
        """
        Runs the actual mapping process and does following things (in order)
        
        1) Translates raw data given to the class (in the data property) and 
           stores it as properties.
        
        2) Maps the data to database objects, and create new ones if necessary.
           Following objects are mapped (in order)
           *) Category
           *) Manufacturer
           *) Product
        """
        if not isinstance(self.data, dict):
            raise ValueError('data property is expected to be a dictionary')
        
        for attr in self.fields.keys():
            # If there is a set_... method, use it to return the value, otherwise
            
            value = self.data[attr] if attr in self.data else None
            
            if hasattr(self, 'set_%s' % attr):
                value = getattr(self, 'set_%s' % attr)(value)
            
            self.fields[attr] = value
            
        # FIXME: Might need to move out to separate routine
        
        self.map_manufacturer()
        self.map_category()
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
            print "Created new manufacturer: %s" % name
        
        
    # NOTE: This is identical to manufacturer mostly by coincidence. These should
    # be different methods
    def map_category(self):
        """
        Attempts to locate manufacturer matching the collected. If it can't, a
        new one will be created.
        """
        
        name = self.fields['category_name']
        
        if not name:
            # FIXME: At this point we've got a problem, and we should probably
            # stop. Best way of stopping is to throw a new kind of exception
            # that the reader listens to. Like ARImporterException
            return
        

        self.category, created = Category.objects.get_or_create(name=name)
        
        if created:
            print "Created new category: %s" % name
        
    def map_product(self):
        """
        Attempts to map the given data to an existing product.
        """
        
        try:
            self.product = Product.objects.get(
                Q(manufacturer__id__exact=self.manufacturer.id),
                Q(product_name__exact=self.fields['product_name'])
                |
                Q(sku__exact=self.fields['product_name']),
            )
        except ObjectDoesNotExist:
            self.product = self.create_product()
            
            # call create object and return
        else:
            self.update_product()
        
        self.map_product_options()
        self.map_product_image()
        
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
        
        print "Created product %s" % product.product_name
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
        
        print "Updated product %s" % self.product.product_name
        self.product.save()
    
    def map_product_options(self):
        """
        Updates, or adds options for the product. This method doesn't remove
        any options.
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
                    print 'No mapping for option type %s' % key
                
                if not value:
                    continue
                
                # FIXME: One could move this code to the Option or Product class                
                opt, created = Option.objects.get_or_create(option_type=option_type, value=value)
                
                if created:
                    print "Created option '%s: %s'" % (option_type.name, value)
                
                if not self.product.options.filter(pk=opt.pk):
                    print "Attaching option '%s: %s'" % (option_type.name, value)
                    self.product.options.add(opt)
    
    def map_product_image(self):
        """
        Fetches the file specified in 'product_image' and assigns it to the 
        product 
        """
        if not 'product_image_url' in self.fields or not self.fields['product_image_url']:
            return
        
        (url, name) = re.match(r'^.+/(.+)$', self.fields['product_image_url']).group(0,1)
        
        sitepath = '%s/%s_%s' % (PRODUCT_IMAGE_BASE, self.fields['vendor_name'], name)
        
        if not default_storage.exists(sitepath):
            print "Downloading product image %s" % url        
            temppath = fetcher.fetch(url)
            default_storage.save(sitepath, File(open(temppath)))
            
            self.product.product_image = sitepath
            self.product.save()
            
        
        # FIXME: Update product
        
        # FIXME: Delete temppath? Can it be done implictly when the process
        # exists?
        
        
        
        