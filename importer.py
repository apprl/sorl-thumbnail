import django
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
import pinax
from pprint import pprint
from os.path import join
import csv, codecs, cStringIO, re, sys

from apparelrow.apparel.models import *


class DataMapper():
    
    # Lookups
    category          = None      # Category instance
    manufacturer      = None      # Manufacturer instance
    
    # Product data fields
    fields = {
        'sku': None,                # Product ID, should be unique with manufacturer
        'product_name': None,       # Product name
        'gender': None,             # F, M or U
        'category_name': None,      # Identifies a category
        'manufacturer_name': None,  # Identifies a manufacturer
    }
    
    # Options
    options = []                    # List of options as tuples (option name: value)
    
    def __init__(self, data={}):
        self.data = data
    
    def translate(self):
        """
        Runs the actual mapping process and does following things (in order)
        
        1) Translates raw data given to the class (in the data property) and 
           stores it as properties.
        
        2) Maps the data to database objects, and create new ones if necessary.
           Following objects are mapped (in order)
           1) Category
           2) Manufacturer
           3) Product
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
    
        self.set_product_options()
        
        # Record that the object was dealt with
    
    def create_product(self):
        """
        Creates a new product with the data collected in 'fields'.
        
        This method is expected to return the newly created product.
        """
        product = Product(
            product_name=self.fields['product_name'],
            sku=self.fields['sku'],
            manufacturer=self.manufacturer,
            gender=self.fields['gender'],
        )
        
        print "Created product"
        product.save()
        
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
        
        print "Updating product"
        self.product.save()
    
    def set_product_options(self):
        """
        Updates, or adds options for the product. This method doesn't remove
        any options.
        """
        pass
        
        

class FashionIslandDataMapper(DataMapper):
    
    def set_sku(self, value):
        
        if 'product_id' in self.data:
            return self.data['product_id']
    
        return None
    
    def set_category_name(self, value):
        if not value:
            return
        
        if not value and 'product_name' in self.data and self.data['product_name'] == 'Leon Jacket':
            return 'Jacket'
        
        # Strip useless pre/suffixes
        
        value = re.sub(ur'-?(?:F.rstasidan|erbjudanden)-?', '', value)
        
        print "VALUE: %s" % value

        
        # Remove double "T-shirt"
        value = re.sub(r'^T-shirt-(?=T-shirts)$', '', value)
        
        # Always in plural
        value = re.sub(r'^T-shirt$', 'T-shirts', value)
        
        return value
    
    def set_gender(self, value):
        if value.lower() == 'mens':
            return 'M'
        elif value.lower() == 'womens':
            return 'F'
        else:
            print "Unrecognised value: %s" % value
            return 'U'
    


class fashionisland_dialect(csv.Dialect):
    lineterminator = '\n'
    delimiter = '|'
    quoting = csv.QUOTE_NONE

csv.register_dialect('fashionisland', fashionisland_dialect)

file = open('data.csv')

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.DictReader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return dict([(k, unicode(v, "utf-8")) for (k, v) in row.items()])

    def __iter__(self):
        return self


reader = UnicodeReader( 
    file, 
    encoding='iso-8859-1',
    fieldnames=('category_name',     # 0 
                'manufacturer_name', # 1 
                'product_name',      # 2 
                'size',              # 3 
                'product_id',        # 4 
                'price',             # 5 
                'delivery_price',    # 6 
                'delivery_time',     # 7 
                'available',         # 8 
                'product_url',       # 9 
                'product_image_url', # 10 
                'description',       # 11
                'gender'             # 12
    ),
    dialect='fashionisland'
)


for row in reader:
    
    x = FashionIslandDataMapper(row)
    x.translate()


