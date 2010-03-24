import re, decimal, copy

from django.test import TestCase
from apparelrow.apparel.models import *
from apparelrow.importer.api import API, IncompleteDataSet, ImporterException
from django.core.exceptions import ObjectDoesNotExist


sample_dict = {
    'version': '0.1',
    'date': '2010-03-09T18:38:00ZCET',
    'vendor': u'Cool Clothes Store',
    'product': {
        'product-id': u'c001',
        'product-name': u'A cool pair of Jeans',
        'categories': [u'Jeans'],
        'manufacturer': u'WhateverMan',
        'price': '239.0',
        'currency': 'GBP',
        'delivery-cost': '10',
        'delivery-time': '1-2 D',
        'availability': '35',
        'image-url': 'http://www.example.com/image.jpg',
        'product-url': 'https://www.example.com/c001',
        'description': u'This is a cool par of whatever',
        'variations': [
            {
                'size': u'M',
                'color': u'blue',
                'availability': True,
            },
            {
                'size': u'L',
                'availability': True,
            },
            {
                'size': u'XS',
                'availability': '24',
            }
        ]            
    }
}


class TestImporterAPIBasic(TestCase):
    """
    Perform basic API operations
    """
    def setUp(self):
        self.dataset = copy.deepcopy(sample_dict)
        
    def test_validation(self):
        a = API()
        a.dataset = self.dataset
        self.assertTrue(a.validate(), 'Validate dataset')
        
        a.dataset['version'] = 'xxx'
        self.assertRaises(ImporterException, a.validate)
    
    #
    # MANUFACTURER
    #    
    def test_manufacturer(self):
        a = API()
        
        self.dataset['product']['manufacturer'] = 'The Manufacturer'
        a.dataset = self.dataset
        
        self.assertTrue(isinstance(a.manufacturer, Manufacturer), 'Created manufacturer')
        
    def test_manufacturer_retrieve(self):
        m = Manufacturer.objects.create(name='My name')
        a = API()
        a.dataset = self.dataset
        a.dataset['product']['manufacturer'] = m.name
        
        api_m = a.manufacturer
        self.assertTrue(isinstance(api_m, Manufacturer), 'Retrieved manufacturer')
        self.assertEqual(m.id, api_m.id, 'Got the same object back')

    def test_manufacturer_validation(self):
        a = API()
        
        del self.dataset['product']['manufacturer']
        a.dataset = self.dataset
        self.assertRaises(IncompleteDataSet, lambda: a.manufacturer)


    #
    # VENDOR
    #
    def test_vendor(self):
        a = API()
        
        self.assertRaises(IncompleteDataSet, lambda: a.vendor)
        
        self.dataset['vendor'] = 'The Vendor'
        a.dataset = self.dataset
        
        v = a.vendor
        self.assertTrue(isinstance(v, Vendor), 'Created vendor')
    
    def test_vendor_retrieve(self):
        v = Vendor.objects.create(name='My Vendor Name')
        a = API()
        a.dataset = self.dataset
        a.dataset['vendor'] = v.name
        
        self.assertTrue(isinstance(a.vendor, Vendor), 'Retrieved vendor')
        self.assertEqual(a.vendor.id, v.id, 'Got the same object back')
    
    def test_vendor_validation(self):
        a = API()
        del self.dataset['vendor']
        a.dataset = self.dataset
        
        self.assertRaises(IncompleteDataSet, lambda: a.vendor)
    

    #
    # CATEGORIES
    #        
    def test_category_single(self):
        self.dataset['product']['categories'] = 'Single Category'
        
        a = API()
        a.dataset = self.dataset
        c = a.category
        
        self.assertTrue(isinstance(c, Category), 'Created category (single)')
        self.assertEqual(c.name, 'Single Category', 'Got correct category')
    
    def test_category_list(self):
        root = Category.objects.create(name='Root')
        a = API()
        a.dataset = self.dataset
        a.dataset['product']['categories'] = [root.name, 'Sub 1', 'Sub 2']
        
        c = a.category
        self.assertTrue(isinstance(c, Category), 'Got category')
        self.assertEqual(c.name,        'Sub 2', 'Returned last category')
        self.assertEqual(c.parent.name, 'Sub 1', 'Created parent category')
        self.assertEqual(c.parent.parent.name, root.name, 'Parent assigned to root')
        self.assertEqual(c.parent.parent.id, root.id, 'Root category retrieved from database')
    
    def test_category_validate(self):
        a = API()
        a.dataset = self.dataset
        del a.dataset['product']['categories']
        self.assertRaises(IncompleteDataSet, lambda: a.category)
    
    
    def test_import_product_image(self):
        # Check that dummy URL is downloaded and Image object created
        # Create FileFetcher class for this.
        pass        
        
        
        
    
class TestImporterAPIProduct(TestCase):
    """
    Test importing a product and all related objects
    """        
    
    def setUp(self):
        self.dataset = copy.deepcopy(sample_dict)
        self.api = API()
        self.api.dataset = self.dataset
        
        self.type_size  = OptionType.objects.create(name='size', description='Size')
        self.type_color = OptionType.objects.create(name='color', description='The colour')
        
        self.category = Category.objects.create(name=self.dataset['product']['categories'][0])
        self.category.option_types.add(self.type_size)
        self.category.option_types.add(self.type_color)
        
        self.manufacturer = Manufacturer.objects.create(name=self.dataset['product']['manufacturer'])
    
    
    # 
    # PRODUCT
    #
    def test_product(self):
        p = self.api.import_product()
        
        self.assertTrue(isinstance(p, Product), 'Returned product')
        self.assertEqual(p.manufacturer.id, self.api.manufacturer.id, 'Manufacturer assigned')
        self.assertEqual(p.category.id, self.api.category.id, 'Category set')
        self.assertEqual(p.sku, self.dataset['product'].get('product-id'), 'SKU property populated')
        self.assertEqual(p.product_name, self.dataset['product'].get('product-name'), 'product name property populated')
        self.assertEqual(p.description,  self.dataset['product'].get('description'),  'Description populated')
        

    def test_product_modify(self):
        p = Product.objects.create(product_name='A name', manufacturer=self.manufacturer, sku=self.dataset['product']['product-id'], category=self.category)
        a = API()
        a.dataset = self.dataset
        a.dataset['product']['product_name'] = 'A Brand New Name'
        a.dataset['product']['description'] = 'The new description'
        a.dataset['product']['categories'] = ['A Brand New Category']
        
        p2 = a.import_product()
        self.assertEqual(p2.id, p.id, 'Product updated')
        self.assertNotEqual(p2.product_name, p.product_name, 'Product name NOT changed')
        self.assertEqual(p2.description, 'The new description', 'Product descrption changed')
        self.assertNotEqual(p2.category.id, p.category.id, 'Product category changed')
    
        
    def test_product_vendor(self):
        p = self.api.import_product()
        vp = VendorProduct.objects.get( product=p, vendor=self.api.vendor )
        
        self.assertTrue(isinstance(vp, VendorProduct), 'Created vendor product')
        self.assertEqual(vp.buy_url,    self.dataset['product']['product-url'], 'buy_url property')
        self.assertEqual(vp.price,      decimal.Decimal(self.dataset['product']['price']),    'price property')
        self.assertEqual(vp.currency,   self.dataset['product']['currency'], 'currency property')
        
        
    def test_product_vendor_modify(self):
        p = self.api.import_product()
        vp = VendorProduct.objects.get( product=p, vendor=self.api.vendor )
        
        self.api.dataset['product']['currency'] = 'SEK'
        p2 = self.api.import_product()
        vp2 = VendorProduct.objects.get( product=p2, vendor=self.api.vendor )
        self.assertEqual(vp2.id, vp.id, 'Same product updated')
        self.assertEqual(vp2.currency, 'SEK', 'Currency updated')


    def test_product_options(self):
        p = self.api.import_product()
        
        self.assertEqual(len(p.options.all()), 4, 'Got four product options')
        self.assertTrue(p.options.filter(option_type=self.type_size, value='M'), 'Added size "M"')
        self.assertTrue(p.options.filter(option_type=self.type_size, value='L'), 'Added size "L"')
        self.assertTrue(p.options.filter(option_type=self.type_size, value='XS'), 'Added size "XS"')
        self.assertTrue(p.options.filter(option_type=self.type_color, value='blue'), 'Added colour "blue"')
    
    def test_product_options_modify(self):
        o1 = Option.objects.create(option_type=self.type_size, value='M')
        o2 = Option.objects.create(option_type=self.type_size, value='L')
        
        temp = Product.objects.create(product_name=self.dataset['product']['product-name'], manufacturer=self.manufacturer, sku=self.dataset['product']['product-id'], category=self.category)
        temp.options.add(o2)
        
        p = self.api.import_product()

        self.assertEqual(len(p.options.all()), 4, 'Got four product options')
        self.assertTrue(p.options.filter(pk=o1.pk), 'Exiting option assigned to product')
        self.assertTrue(p.options.filter(pk=o2.pk), 'Exiting option untouched')
        self.assertTrue(p.options.filter(option_type=self.type_size, value='XS'), 'Added size "M"')
        self.assertTrue(p.options.filter(option_type=self.type_color, value='blue'), 'Added colour "blue"')
    
    
    def test_product_availability(self):
        p  = self.api.import_product()
        vp = VendorProduct.objects.get(product=p, vendor=self.api.vendor)
        
        self.assertEqual(len(vp.variations.all()), 3, 'Three variations imported')
        
        # NOTE: This test relies on that the API is creating new options in the order
        # they appear in the data passed to import_product
        
        var_1 = vp.variations.get(id=1)
        self.assertEqual(var_1.in_stock, -1, 'Got correct stock level for Medium/Blue')
        self.assertTrue(var_1.options.get(option_type=self.type_color, value='blue'), 'Got color: blue option')
        self.assertTrue(var_1.options.get(option_type=self.type_size, value='M'), 'Got size: m option')

        var_2 = vp.variations.get(id=2)
        self.assertEqual(var_2.in_stock, -1, 'Got correct stock level for Large')
        self.assertTrue(var_2.options.get(option_type=self.type_size, value='L'), 'Got size: L option')


        var_3 = vp.variations.get(id=3)
        self.assertEqual(var_3.in_stock, 24, 'Got correct stock level for XtraSmall')
        self.assertTrue(var_3.options.get(option_type=self.type_size, value='XS'), 'Got size: xs option')

    def test_product_availability_modify(self):
        # FIXME: This test is a bit lengthy, but it covers all aspects of the 
        # behaviour when modifying availability for an existing product/vendor
        
        p  = self.api.import_product()
        vp = VendorProduct.objects.get(product=p, vendor=self.api.vendor)
        original_var_1 = vp.variations.get(id=1)
        
        d = self.dataset
        d['product']['variations'].append({
            'size': 'M',
            'color': 'red',
            'availability': False
        }) 
        del d['product']['variations'][0]['availability']
        d['product']['variations'][1]['availability'] = '1'
        d['product']['variations'][2]['color'] = 'green'
        
        a = API()
        a.dataset = d
        p  = a.import_product()
        vp = VendorProduct.objects.get(product=p, vendor=a.vendor)
        
        # No availability property in input data, will result in NULL (None)
        var_1 = vp.variations.get(id=original_var_1.id) # Ensure that the same object is retrieved
        self.assertEqual(var_1.in_stock, None, 'Got correct stock level for Medium/Blue')
        self.assertTrue(var_1.options.get(option_type=self.type_color, value='blue'), 'Got color: blue option')
        self.assertTrue(var_1.options.get(option_type=self.type_size, value='M'), 'Got size: m option')
        
        # Changed availability
        var_2 = vp.variations.get(id=2)
        self.assertEqual(var_2.in_stock, 1, 'Got correct stock level for Large')
        self.assertTrue(var_2.options.get(option_type=self.type_size, value='L'), 'Got size: L option')

        # Untouched variation left alone
        var_3 = vp.variations.get(id=3)
        self.assertEqual(var_3.in_stock, 24, 'Got correct stock level for XtraSmall')
        self.assertTrue(var_3.options.get(option_type=self.type_size, value='XS'), 'Got size: xs option')
        
        # Changed definition creates new variation
        var_4 = vp.variations.get(id=4)
        self.assertEqual(var_4.in_stock, 24, 'Got correct stock level for XtraSmall/Green')
        self.assertTrue(var_4.options.get(option_type=self.type_size, value='XS'), 'Got size: xs option')
        self.assertTrue(var_4.options.get(option_type=self.type_color, value='green'), 'Got color: green option')

        # Added new variation
        var_5 = vp.variations.get(id=5)
        self.assertEqual(var_5.in_stock, 0, 'Got correct stock level for Medium/Red')
        self.assertTrue(var_5.options.get(option_type=self.type_size, value='M'), 'Got size: xs option')
        self.assertTrue(var_5.options.get(option_type=self.type_color, value='red'), 'Got color: red option')

        