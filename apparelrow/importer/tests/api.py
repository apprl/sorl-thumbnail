import re, decimal, copy, os, shutil, time

from django.test import TestCase, TransactionTestCase
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from apparel.models import *
from importer.models import ImportLog, VendorFeed
from importer.api import API, IncompleteDataSet, ImporterException


sample_dict = {
    'version': '0.1',
    'date': '2010-03-09T18:38:00ZCET',
    'vendor': u'Cool Clothes Store',
    'product': {
        'product-id': u'c001',
        'product-name': u'A cool pair of Jeans',
        'categories': u'Jeans',
        'manufacturer': u'WhateverMan',
        'price': '239.0',
        'currency': 'GBP',
        'delivery-cost': '10',
        'delivery-time': '1-2 D',
        'availability': '35',
        'image-url': 'http://localhost:8000/site_media/static/_test/__image.png',
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
        self.log     = ImportLog.objects.create(
                            vendor_feed=VendorFeed.objects.create(
                                name='testfeed',
                                url='http://example.com',
                                vendor=Vendor.objects.create(name='Cool Clothes Store'),
                                provider_class='sample',
                            ),
                       )
        
    def test_validation(self):
        a = API(import_log=self.log)
        a.dataset = self.dataset
        self.assertTrue(a.validate(), 'Validate dataset')
        
        a.dataset['version'] = 'xxx'
        self.assertRaises(ImporterException, a.validate)
    
    #
    # MANUFACTURER
    #    
    def test_manufacturer(self):
        a = API(import_log=self.log)
        
        self.dataset['product']['manufacturer'] = 'The Manufacturer'
        a.dataset = self.dataset
        
        self.assertTrue(isinstance(a.manufacturer, Manufacturer), 'Created manufacturer')
        
    def test_manufacturer_retrieve(self):
        m = Manufacturer.objects.create(name='My name')
        a = API(import_log=self.log)
        a.dataset = self.dataset
        a.dataset['product']['manufacturer'] = m.name
        
        api_m = a.manufacturer
        self.assertTrue(isinstance(api_m, Manufacturer), 'Retrieved manufacturer')
        self.assertEqual(m.id, api_m.id, 'Got the same object back')

    def test_manufacturer_validation(self):
        a = API(import_log=self.log)
        
        del self.dataset['product']['manufacturer']
        a.dataset = self.dataset
        self.assertRaises(IncompleteDataSet, lambda: a.manufacturer)


    #
    # VENDOR
    #
    def test_vendor(self):
        a = API(import_log=self.log)
        
        self.assertRaises(IncompleteDataSet, lambda: a.vendor)
        
        a.dataset = self.dataset
        
        v = a.vendor
        self.assertTrue(isinstance(v, Vendor), 'Created vendor')
    
    def test_vendor_retrieve(self):
        v = self.log.vendor_feed.vendor
        a = API(import_log=self.log)
        a.dataset = self.dataset
        a.dataset['vendor'] = v.name
        
        self.assertTrue(isinstance(a.vendor, Vendor), 'Retrieved vendor')
        self.assertEqual(a.vendor.id, v.id, 'Got the same object back')
    
    def test_vendor_validation(self):
        a = API(import_log=self.log)
        del self.dataset['vendor']
        a.dataset = self.dataset
        
        self.assertRaises(IncompleteDataSet, lambda: a.vendor)
    

    #
    # CATEGORIES
    #        
    def test_new_category(self):
        self.dataset['product']['categories'] = 'Single Category'
        
        a = API(import_log=self.log)
        a.dataset = self.dataset
                
        self.assertTrue(a.category is None, 'No category returned')
        
        try:
            v = VendorCategory.objects.get(vendor=a.vendor, name='Single Category')
        except:
            self.fail('VendorCategoy created with new category')
        else:
            self.assertTrue(True, 'VendorCategory created for category')
        
        self.assertTrue(self.log.messages.get(status='attention', message__contains=v.__unicode__()), 'Log message created')
    
    def test_existing_category(self):
        self.dataset['product']['categories'] = 'Existing Category'
        vc = VendorCategory.objects.create(
            vendor=self.log.vendor_feed.vendor, 
            name='Existing Category',
            category=Category.objects.create(name='The Category')
        )
        
        a = API(import_log=self.log)
        a.dataset = self.dataset
        
        self.assertEquals(a.category, vc.category, 'Found category through VendorCategory')
        self.assertEquals(a._category, vc, 'Found VendorCategory from name')
    
    def test_multiple_categorues(self):
        self.dataset['product']['categories'] = ['Cat 1', 'Cat 2']
        
        a = API(import_log=self.log)
        a.dataset = self.dataset
        
        self.assertTrue(a.category is None, 'No category mapped')
        self.assertEquals(a._category.name, 'Cat 1 Cat 2', 'Multiple categories joined')

    def test_category_validate(self):
        a = API(import_log=self.log)
        a.dataset = self.dataset
        del a.dataset['product']['categories']
        self.assertRaises(IncompleteDataSet, lambda: a.category)
    
    
    def test_import_product_image(self):
        # Check that dummy URL is downloaded and Image object created
        # Create FileFetcher class for this.
        pass        
        
        
        
    
class TestImporterAPIProduct(TransactionTestCase):
    """
    Test importing a product and all related objects
    """        
    
    def setUp(self):
        self.log = ImportLog.objects.create(
             vendor_feed=VendorFeed.objects.create(
                 name='testfeed',
                 url='http://example.com',
                 vendor=Vendor.objects.create(name='Cool Clothes Store'),
                 provider_class='sample',
             ),
        )
        self.dataset = copy.deepcopy(sample_dict)
        self.api = API(import_log=self.log)
        self.api.dataset = self.dataset
        
        self.type_size  = OptionType.objects.create(name='size', description='Size')
        self.type_color = OptionType.objects.create(name='color', description='The colour')
        
        self.category = Category.objects.create(name=self.dataset['product']['categories'])
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
        self.assertEqual(p.category, None, 'Category (not) mapped')
        self.assertEqual(p.sku, self.dataset['product'].get('product-id'), 'SKU property populated')
        self.assertEqual(p.product_name, self.dataset['product'].get('product-name'), 'product name property populated')
        self.assertEqual(p.description,  self.dataset['product'].get('description'),  'Description populated')
        

    def test_product_modify(self):
        p = Product.objects.create(product_name='A name', manufacturer=self.manufacturer, sku=self.dataset['product']['product-id'], category=self.category)
        a = API(import_log=self.log)
        a.dataset = self.dataset
        a.dataset['product']['product_name'] = 'A Brand New Name'
        a.dataset['product']['description'] = 'The new description'
        a.dataset['product']['categories'] = ['A Brand New Category']
        
        p2 = a.import_product()
        self.assertEqual(p2.id, p.id, 'Product updated')
        self.assertNotEqual(p2.product_name, p.product_name, 'Product name NOT changed')
        self.assertEqual(p2.description, 'The new description', 'Product descrption changed')
        self.assertNotEqual(p2.category, p.category, 'Product category changed')
    
        
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
        
        self.assertEqual(p.options.count(), 4, 'Got four product options')
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

        self.assertEqual(p.options.count(), 4, 'Got four product options')
        self.assertTrue(p.options.filter(pk=o1.pk), 'Exiting option assigned to product')
        self.assertTrue(p.options.filter(pk=o2.pk), 'Exiting option untouched')
        self.assertTrue(p.options.filter(option_type=self.type_size, value='XS'), 'Added size "M"')
        self.assertTrue(p.options.filter(option_type=self.type_color, value='blue'), 'Added colour "blue"')
    
    
    def test_product_availability(self):
        p  = self.api.import_product()
        vp = VendorProduct.objects.get(product=p, vendor=self.api.vendor)
        
        self.assertEqual(vp.variations.count(), 3, 'Three variations imported')
        
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


    def test_product_availability_null(self):
        del self.api.dataset['product']['variations'][0]['availability']
        p  = self.api.import_product()
        vp = VendorProduct.objects.get(product=p, vendor=self.api.vendor)
        
        var_1 = vp.variations.get(id=1)
        self.assertEqual(var_1.in_stock, None, 'Got correct stock level when availability attribute is missing')
    
    def test_product_availability_true(self):
        self.api.dataset['product']['variations'][0]['availability'] = True
        p  = self.api.import_product()
        vp = VendorProduct.objects.get(product=p, vendor=self.api.vendor)
        
        var_1 = vp.variations.get(id=1)
        self.assertEqual(var_1.in_stock, -1, 'Got correct stock level when availability is true')
    
    def test_product_availability_false(self):
        self.api.dataset['product']['variations'][0]['availability'] = False
        p  = self.api.import_product()
        vp = VendorProduct.objects.get(product=p, vendor=self.api.vendor)
        
        var_1 = vp.variations.get(id=1)
        self.assertEqual(var_1.in_stock, 0, 'Got correct stock level when availability is false')
    
    def test_product_availability_modify(self):
        p  = self.api.import_product()
        vp = VendorProduct.objects.get(product=p, vendor=self.api.vendor)
        original_in_stock_1 = vp.variations.get(id=1).in_stock
        original_in_stock_2 = vp.variations.get(id=2).in_stock
        
        # Add new item
        self.dataset['product']['variations'].append({
            'size': 'M',
            'color': 'red',
            'availability': '5'
        }) 
        # Change availability for first item
        self.dataset['product']['variations'][0]['availability'] = '10'
        # Modify spec for combination item (should create new variation)
        self.dataset['product']['variations'][1]['color'] = 'black'
        
        # Run import again
        a = API(import_log=self.log)
        a.dataset = self.dataset
        p  = a.import_product()
        vp = VendorProduct.objects.get(product=p, vendor=a.vendor)
        
        # Check that stock level changed
        self.assertEqual(vp.variations.count(), 5, 'Got five variations')
        self.assertEqual(vp.variations.get(id=1).in_stock, 10, 'In stock set to correct value')
        self.assertNotEqual(vp.variations.get(id=1).in_stock, original_in_stock_1, 'in_stock property changed')
        
        # Assert that stock level was unchanged for second
        self.assertEqual(vp.variations.get(id=2).in_stock, original_in_stock_2, 'In stock not changed')
        self.assertTrue(vp.variations.get(id=2).options.get(option_type=self.type_size, value='L'), 'Option unchanged')
        self.assertRaises(ObjectDoesNotExist, lambda: vp.variations.get(id=2).options.get(option_type=self.type_color, value='black'))
        
        # Assert that update options yields new variation (old is preserved)
        self.assertTrue(vp.variations.get(id=4), 'New item created')
        self.assertTrue(vp.variations.get(id=4).options.get(option_type=self.type_color, value='black'), 'New item created with red color')
        self.assertTrue(vp.variations.get(id=4).options.get(option_type=self.type_size, value='L'), 'Changed item, old property remain')
        
        # Assert that fourth item created new variation
        self.assertTrue(vp.variations.get(id=5), 'New item created')
        self.assertEqual(vp.variations.get(id=5).in_stock, 5, 'New item created')
        self.assertTrue(vp.variations.get(id=5).options.get(option_type=self.type_color, value='red'), 'New item created with red color')
        self.assertTrue(vp.variations.get(id=5).options.get(option_type=self.type_size, value='M'), 'New item created with red color')


class TestProductImage(TestCase):
    def setUp(self):
        self.log = ImportLog.objects.create(
             vendor_feed=VendorFeed.objects.create(
                 name='testfeed',
                 url='http://example.com',
                 vendor=Vendor.objects.create(name='Cool Clothes Store'),
                 provider_class='sample',
             ),
        )
        self.api = API(import_log=self.log)
        self.api.dataset = copy.deepcopy(sample_dict)
        
        # Create sample directory at 
    
    def tearDown(self):
        # FIXME: Remove local image if it eixsts
        fp = os.path.join(settings.MEDIA_ROOT, settings.APPAREL_PRODUCT_IMAGE_ROOT, 'cool-clothes-store', '__image.jpg')
        if os.path.exists(fp):
            os.remove(fp)
    
    def test_product_image_path(self):
        self.assertTrue(settings.APPAREL_PRODUCT_IMAGE_ROOT, 'APPAREL_PRODUCT_IMAGE_ROOT setting exists')
        self.assertEqual(
            self.api.product_image_path(self.api.dataset['product']['image-url']), 
            '%s/%s/%s' % (
                settings.APPAREL_PRODUCT_IMAGE_ROOT, 
                'cool-clothes-store', 
                '__image.png'
            )
        )
        
    def test_product_image_no_url(self):
        self.assertRaises(IncompleteDataSet, self.api.product_image_path, None)
        
    def test_product_image(self):
        print 'Currently no way of testing a request against testserver using urllib2.'
        # FIXME: Implement this test somehow.
        #
        #p = self.api.product_image()
        #
        #self.assertEqual(p, self.api.product_image_path, "Returns product_image_path property")
        #self.assertTrue(os.path.exists(os.path.join(settings.MEDIA_ROOT, p)), 'File downloaded')
        #
    def test_product_image_http_error(self):
        self.api.dataset['product']['image-url'] = 'http://www.example.com/404.jpg'
        
        try:
            # FIXME: assertRaises only works on callables
            self.api.product_image
        except IncompleteDataSet:
            self.assertTrue(True, 'Require URL to exist')
        else:
            self.fail('Require URL to eist')
    
    def test_product_image_exists(self):
        target_file = os.path.join(
            settings.MEDIA_ROOT, 
            self.api.product_image_path(self.api.dataset['product']['image-url'])
        )
        shutil.copy(os.path.join(settings.STATIC_ROOT, '_test', '__image.png'), target_file)
        stat = os.stat(target_file)
        time.sleep(2) # Wait for time from 
        
        p = self.api.product_image
        self.assertEqual(stat.st_mtime, os.stat(os.path.join(settings.MEDIA_ROOT, p)).st_mtime, 'File not change after downloading')
        
    def test_product_image_missing(self):
        del self.api.dataset['product']['image-url']
         
        try:
            self.api.product_image
        except IncompleteDataSet:
            self.assertTrue(True, 'Require URL property to be a string')
        else:
            self.fail('Require URL property to be a string')
    
    def test_product_image_import(self):
        """
        Product image is downloaded during import
        """
        print 'Currently no way of testing a request against testserver using urllib2.'
        # FIXME: Implement this test somehow.
        #
        #p = self.api.import_product()
        #self.assertTrue(os.path.exists(os.path.join(settings.MEDIA_ROOT, self.api.product_image_path)), 'Image downloaded during import')
        #self.assertEqual(p.product_image, self.api.product_image_path, 'image_path stored in product')

class TestDataSetImport(TransactionTestCase):
    def setUp(self):
        self.log = ImportLog.objects.create(
             vendor_feed=VendorFeed.objects.create(
                 name='testfeed',
                 url='http://example.com',
                 vendor=Vendor.objects.create(name='Cool Clothes Store'),
                 provider_class='sample',
             ),
        )
        self.api = API(import_log=self.log)
        self.dataset = copy.deepcopy(sample_dict)
    
    def test_import_successful(self):
        self.api.dataset = self.dataset
        p = self.api.import_dataset()
        
        self.assertTrue(isinstance(p, Product), 'Data imported using default dataset')
        # Note: This test is not ensuring all related data was created. See
        # above tests for that.
        
    def test_import_successful_data(self):
        p = self.api.import_dataset(data=self.dataset)
        
        self.assertTrue(isinstance(p, Product), 'Data using passed dataset')
    
    def test_import_validation(self):
        self.dataset['version'] = 'xxx'
        self.assertRaises(ImporterException, self.api.import_dataset, self.dataset)
    
    def test_import_rollback(self):
        self.dataset['product']['manufacturer'] = None
        
        self.assertRaises(IncompleteDataSet, self.api.import_dataset, self.dataset)
        
        if Category.objects.count() > 0:
            self.fail('Objects not rolled back, are all product-related tables created with the InnoDB engine?')
        