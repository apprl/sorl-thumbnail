import re, os, shutil, time, copy
from datetime import datetime, date
from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.conf import settings
from mock import Mock

from django.core.exceptions import ObjectDoesNotExist

from apparelrow.importer.fxrates import FXRateImporter
from apparelrow.importer.framework.mapper import DataMapper, SkipField
from apparelrow.importer.framework.provider import Provider, load_provider, CSVProvider
from apparelrow.importer.models import ImportLog, VendorFeed, FXRate
from apparelrow.apparel import models as apparel
from apparelrow.importer.models import VendorFeed
from apparelrow.importer.api import API, IncompleteDataSet, ImporterError, SkipProduct
import unittest


""" FXRate """
class FXRateImporterTest(TestCase):
    def setUp(self):
        self.sample_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures/fxrates-samples.xml')

    def tearDown(self):
        pass

    def test_settings(self):
        self.assertTrue(settings.APPAREL_BASE_CURRENCY)
        self.assertTrue(settings.APPAREL_FXRATES_URL)

    def test_import_new_fxrate(self):
        importer = FXRateImporter(
            base_currency=settings.APPAREL_BASE_CURRENCY
        )

        self.assertTrue(importer.import_fx_rate('USD', 6.38), 'Imported FX Rate')

        fxrate = FXRate.objects.filter(
            base_currency=settings.APPAREL_BASE_CURRENCY,
            currency='USD'
        )

        self.assertEquals(len(fxrate), 1)
        self.assertEqual(fxrate[0].currency, 'USD')
        self.assertEqual(fxrate[0].base_currency, settings.APPAREL_BASE_CURRENCY)
        self.assertEqual(fxrate[0].rate, Decimal('6.38'))

    def test_import_existing_fxrate(self):
        importer = FXRateImporter(
            base_currency='BRL'
        )

        self.assertTrue(importer.import_fx_rate('USD', 6.38),   'Imported FX Rate')
        self.assertTrue(importer.import_fx_rate('USD', '6.58'), 'Imported FX Rate again')

        fxrate = FXRate.objects.filter(
            base_currency=importer.base_currency,
            currency='USD'
        )
        self.assertEqual(len(fxrate), 1)
        self.assertEqual(fxrate[0].currency, 'USD')
        self.assertEqual(fxrate[0].base_currency, 'BRL')
        self.assertEqual(fxrate[0].rate, Decimal('6.58'))

    def test_parse_fxrate_file(self):
        importer = FXRateImporter(
            base_currency='SEK'
        )

        self.assertTrue(importer.import_feed(self.sample_file))
        self.assertEqual(
            [
                (u'ARS', Decimal('0.631380'), u'SEK'),
                (u'EUR', Decimal('0.113460'), u'SEK'),
                (u'GBP', Decimal('0.097210'), u'SEK')
            ],
            list(FXRate.objects.order_by('currency').values_list('currency', 'rate', 'base_currency'))
        )

    def test_parse_fxrate_file_run(self):
        importer = FXRateImporter(
            base_currency='SEK',
            file=self.sample_file
        )

        self.assertTrue(importer.run())
        self.assertEqual(3, FXRate.objects.count())


class FXRateModelTest(TestCase):
    fixtures = ['test-fxrates.yaml']

    def test_model_unicode(self):
        self.assertEqual(
            u'%s' % FXRate.objects.get(pk=1),
            u'1 SEK in BRL = 0.259600'
        )

    def test_convert_amount(self):
        brl = FXRate.objects.get(pk=1)
        self.assertEqual(Decimal('3852.080123'), brl.convert(1000))

    def test_update_prices(self):
        self.assertEqual(4, apparel.VendorProduct.objects.filter(currency=None).count())

        brl = FXRate.objects.get(pk=1)
        brl.update_prices()

        self.assertEqual(2, apparel.VendorProduct.objects.filter(currency=None).count())
        self.assertEqual(Decimal('3852.00'), apparel.VendorProduct.objects.get(pk=1).price)
        self.assertEqual('SEK', apparel.VendorProduct.objects.get(pk=1).currency)
        self.assertEqual(Decimal('4237.00'), apparel.VendorProduct.objects.get(pk=3).price)
        self.assertEqual('SEK', apparel.VendorProduct.objects.get(pk=3).currency)

        apparel.VendorProduct.objects.filter(pk=1).update(_original_price=1050)
        brl.update_prices()

        self.assertEqual(2, apparel.VendorProduct.objects.filter(currency=None).count())
        self.assertEqual(Decimal('4045.00'), apparel.VendorProduct.objects.get(pk=1).price)
        self.assertEqual('SEK', apparel.VendorProduct.objects.get(pk=1).currency)


""" API """
SAMPLE_DICT = {
    'version': '0.1',
    'date': '2010-03-09T18:38:00ZCET',
    'vendor': u'Cool Clothes Store',
    'product': {
        'product-id': u'c001',
        'product-name': u'A cool pair of Jeans',
        'category': u'Jeans',
        'manufacturer': u'WhateverMan',
        'price': '239.0',
        'discount-price': '239.0',
        'currency': 'GBP',
        'delivery-cost': '10',
        'delivery-time': '1-2 D',
        'availability': 35,
        'gender': 'W',
        'image-url': [('http://localhost:8000/site_media/static/_test/__image.png', 200), ],
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
    Tests basic API operations
    """
    def setUp(self):
        self.dataset = copy.deepcopy(SAMPLE_DICT)
        self.log     = ImportLog.objects.create(
                            vendor_feed=VendorFeed.objects.create(
                                name='testfeed',
                                url='http://example.com',
                                vendor=apparel.Vendor.objects.create(name='Cool Clothes Store'),
                                provider_class='sample',
                            ),
                       )

    def test_validate_ok(self):
        """
        Tests validation for valid dataset
        """
        a = API(import_log=self.log)
        a.dataset = self.dataset
        self.assertTrue(a.validate(), 'Validate dataset')

    def test_validate_fields(self):
        """
        Tests validation for datasets with missing fields
        """
        a = API(import_log=self.log)

        for f in ('date', 'version', 'vendor', 'product', ):
            a.dataset = copy.deepcopy(self.dataset)
            del a.dataset[f]
            self.assertRaises(IncompleteDataSet, a.validate)

        for f in ('product-id', 'product-name', 'category', 'manufacturer', 'price', 'currency', 'delivery-cost',
                  'delivery-time', 'availability', 'image-url', 'product-url', 'description', 'variations', 'gender'):
            a.dataset = copy.deepcopy(self.dataset)
            del a.dataset['product'][f]
            self.assertRaises(IncompleteDataSet, a.validate)

    def test_validate_variations(self):
        """
        Tests validation for dataset with wrong type variations
        """
        a = API(import_log=self.log)
        a.dataset = self.dataset
        a.dataset['product']['variations'] = 'Not a list'

        self.assertRaises(IncompleteDataSet, a.validate)

    def test_validate_version(self):
        """
        Tests validation for incompatible version number
        """
        a = API(import_log=self.log)
        a.dataset = self.dataset
        a.dataset['version'] = 'xxx'
        self.assertRaises(ImporterError, a.validate)

    def test_validate_gender(self):
        """
        Tests validation for gender
        """
        a = API(import_log=self.log)
        a.dataset = self.dataset
        a.dataset['product']['gender'] = 'Not valid'
        self.assertRaises(IncompleteDataSet, a.validate)

        a.dataset['product']['gender'] = None
        self.assertTrue(a.validate())

        a.dataset['product']['gender'] = 'W'
        self.assertTrue(a.validate())

    """ MANUFACTURER """
    def test_manufacturer(self):
        """
        Tests dataset's manufacturer is a Brand instance
        """
        m = apparel.Brand.objects.create(name='My brand')
        a = API(import_log=self.log)

        self.dataset['product']['manufacturer'] = m.name
        a.dataset = self.dataset

        self.assertTrue(isinstance(a.manufacturer, apparel.Brand))

    def test_manufacturer_retrieve(self):
        """
        Tests dataset's manufacturer is retrieved correctly
        """
        m = apparel.Brand.objects.create(name='My brand')
        a = API(import_log=self.log)
        a.dataset = self.dataset
        a.dataset['product']['manufacturer'] = m.name

        api_m = a.manufacturer
        self.assertTrue(isinstance(api_m, apparel.Brand), 'Retrieved manufacturer')
        self.assertEqual(m.id, api_m.id, 'Got the same object back')

    """ VENDOR """
    def test_vendor(self):
        """
        Tests dataset's vendor is a Vendor instance
        """
        a = API(import_log=self.log)

        self.assertRaises(IncompleteDataSet, lambda: a.vendor)

        a.dataset = self.dataset
        v = a.vendor
        self.assertTrue(isinstance(v, apparel.Vendor), 'Created vendor')

    def test_vendor_retrieve(self):
        """
        Tests dataset's vendor is retrieved correctly
        """
        v = self.log.vendor_feed.vendor
        a = API(import_log=self.log)
        a.dataset = self.dataset
        a.dataset['vendor'] = v.name

        self.assertTrue(isinstance(a.vendor, apparel.Vendor), 'Retrieved vendor')
        self.assertEqual(a.vendor.id, v.id, 'Got the same object back')

    """ CATEGORIES """
    def test_new_category(self):
        self.dataset['product']['category'] = 'Single Category'

        a = API(import_log=self.log)
        a.dataset = self.dataset

        self.assertTrue(a.category is None, 'No category returned')

        try:
            v = apparel.VendorCategory.objects.get(vendor=a.vendor, name='Single Category')
        except:
            self.fail('VendorCategory created with new category')
        else:
            #TODO IS THIS TEST INCOMPLETE?
            self.assertTrue(True, 'VendorCategory created for category')

        self.assertTrue(self.log.messages.get(status='attention', message__contains=v.__unicode__()), 'Log message created')

    def test_existing_category(self):
        self.dataset['product']['category'] = 'Existing Category'
        vc = apparel.VendorCategory.objects.create(
            vendor=self.log.vendor_feed.vendor,
            name='Existing Category',
            category=apparel.Category.objects.create(name='The Category')
        )

        a = API(import_log=self.log)
        a.dataset = self.dataset

        self.assertEquals(a.category, vc.category, 'Found category through VendorCategory')
        self.assertEquals(a.vendor_category, vc, 'Found VendorCategory from name')

    def test_multiple_categories(self):
        self.dataset['product']['category'] = ['Cat 1', 'Cat 2']

        a = API(import_log=self.log)
        a.dataset = self.dataset

        self.assertTrue(a.category is None, 'No category mapped')
        self.assertEquals(a.vendor_category.name, 'Cat 1 Cat 2', 'Multiple  joined')

    def test_import_product_image(self):
        # Check that dummy URL is downloaded and Image object created
        # Create FileFetcher class for this.
        pass


#TODO Problem with this function, ask Klas
class TestImporterAPIProduct(TransactionTestCase):
    """
    Test importing a product and all related objects
    """

    def setUp(self):
        self.fxrate = FXRate.objects.create(base_currency=settings.APPAREL_BASE_CURRENCY, currency='GBP', rate=Decimal('0.098'))
        self.log = ImportLog.objects.create(
             vendor_feed=VendorFeed.objects.create(
                 name='testfeed',
                 url='http://example.com',
                 vendor=apparel.Vendor.objects.create(name='Cool Clothes Store'),
                 provider_class='sample',
             ),
        )
        self.dataset = copy.deepcopy(SAMPLE_DICT)
        self.api = API(import_log=self.log)
        self.api.dataset = self.dataset
        self.api._product_image = '/dummy/path.jpeg'    # This prevent the tests from trying to download non-existant images

        self.type_size  = apparel.OptionType.objects.create(name='size', description='Size')
        self.type_color = apparel.OptionType.objects.create(name='color', description='The colour')

        self.category = apparel.Category.objects.create(name=self.dataset['product']['category'])
        self.category.option_types.add(self.type_size)
        self.category.option_types.add(self.type_color)
        self.manufacturer = apparel.Brand.objects.create(name=self.dataset['product']['manufacturer'])
        self.product = self.api.import_product()

    """ PRODUCT """
    def test_product(self):
        self.assertTrue(isinstance(self.product, apparel.Product), 'Returned product')
        self.assertEqual(self.product.manufacturer.id, self.api.manufacturer.id, 'Manufacturer assigned')
        self.assertEqual(self.product.category, None, 'Category (not) mapped')
        self.assertEqual(self.product.sku, self.dataset['product'].get('product-id'), 'SKU property populated')
        self.assertEqual(self.product.product_name, self.dataset['product'].get('product-name'), 'product name property populated')
        self.assertEqual(self.product.description, self.dataset['product'].get('description'), 'Description populated')
        self.assertEqual(self.product.gender, self.dataset['product'].get('gender'), 'Gender populated')

    def test_product_modify(self):
        a = API(import_log=self.log)
        a.dataset = self.dataset
        a._product_image = '/dummy/path.jpeg'

        a.dataset['product']['product_name'] = 'A Brand New Name'
        a.dataset['product']['description'] = 'The new description'
        a.dataset['product']['category'] = ['A Brand New Category']

        p2 = a.import_product() #TODO Problem with this function, ask Klas
        self.assertEqual(p2.id, self.product.id, 'Product updated')
        self.assertEqual(p2.product_name, self.product.product_name, 'Product name NOT changed')
        self.assertNotEqual(self.product.description, p2.description, 'Product description changed')
        self.assertEqual(p2.description, 'The new description', 'Product description updated correctly')

    def test_product_vendor(self):
        vp = apparel.VendorProduct.objects.get(product=self.product, vendor=self.api.vendor)

        self.assertTrue(isinstance(vp, apparel.VendorProduct), 'Created vendor product')
        self.assertEqual(vp.buy_url, self.dataset['product']['product-url'], 'buy_url property')
        self.assertEqual(vp.currency, settings.APPAREL_BASE_CURRENCY, 'currency property')
        self.assertEqual(vp.original_price, Decimal(self.dataset['product']['price']), 'original_price property')
        self.assertEqual(vp.original_currency, self.dataset['product']['currency'], 'original_currency property')

        self.assertAlmostEqual(
            vp.price,
            self.fxrate.convert(float(self.dataset['product']['price'])),
            2,
            'price property'
        )

    def test_product_vendor_modify(self):
        vp = apparel.VendorProduct.objects.get(product=self.product, vendor=self.api.vendor)

        self.api.dataset['product']['currency'] = 'SEK'
        p2 = self.api.import_product()
        vp2 = apparel.VendorProduct.objects.get( product=p2, vendor=self.api.vendor)
        self.assertEqual(vp2.id, vp.id, 'Same product updated')
        self.assertEqual(vp2.currency, 'SEK', 'Currency updated')

    def test_product_options(self):

        self.assertEqual(self.product.options.count(), 4, 'Got four product options')
        self.assertTrue(self.product.options.filter(option_type=self.type_size, value='M'), 'Added size "M"')
        self.assertTrue(self.product.options.filter(option_type=self.type_size, value='L'), 'Added size "L"')
        self.assertTrue(self.product.options.filter(option_type=self.type_size, value='XS'), 'Added size "XS"')
        self.assertTrue(self.product.options.filter(option_type=self.type_color, value='blue'), 'Added colour "blue"')

    def test_product_options_modify(self):
        o1 = apparel.Option.objects.get(option_type=self.type_size, value='M')
        o2 = apparel.Option.objects.get(option_type=self.type_size, value='L')

        temp = apparel.Product.objects.create(product_name=self.dataset['product']['product-name'], manufacturer=self.manufacturer, sku=self.dataset['product']['product-id'], category=self.category)
        temp.options.add(o2)

        self.assertEqual(self.product.options.count(), 4, 'Got four product options')
        self.assertTrue(self.product.options.filter(pk=o1.pk), 'Exiting option assigned to product')
        self.assertTrue(self.product.options.filter(pk=o2.pk), 'Exiting option untouched')
        self.assertTrue(self.product.options.filter(option_type=self.type_size, value='XS'), 'Added size "M"')

    #@unittest.skip("Review this test")
    def test_product_availability(self):
        vp = apparel.VendorProduct.objects.get(product=self.product, vendor=self.api.vendor)

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

    #@unittest.skip("Review this test")
    def test_product_availability_null(self):
        del self.api.dataset['product']['variations'][0]['availability']
        vp = apparel.VendorProduct.objects.get(product=self.product, vendor=self.api.vendor)

        var_1 = vp.variations.get(id=1)
        self.assertEqual(var_1.in_stock, None, 'Got correct stock level when availability attribute is missing')

    #@unittest.skip("Review this test")
    def test_product_availability_true(self):
        self.api.dataset['product']['variations'][0]['availability'] = True
        vp = apparel.VendorProduct.objects.get(product=self.product, vendor=self.api.vendor)

        var_1 = vp.variations.get(id=1)
        self.assertEqual(var_1.in_stock, -1, 'Got correct stock level when availability is true')

    #@unittest.skip("Review this test")
    def test_product_availability_false(self):
        self.api.dataset['product']['variations'][0]['availability'] = False
        vp = apparel.VendorProduct.objects.get(product=self.product, vendor=self.api.vendor)

        var_1 = vp.variations.get(id=1)
        self.assertEqual(var_1.in_stock, 0, 'Got correct stock level when availability is false')

    #@unittest.skip("Review this test")
    def test_product_availability_modify(self):
        vp = apparel.VendorProduct.objects.get(product=self.product, vendor=self.api.vendor)
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
        a._product_image = '/dummy/path.jpeg'
        p  = a.import_product()
        vp = apparel.VendorProduct.objects.get(product=p, vendor=a.vendor)

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
                 vendor=apparel.Vendor.objects.create(name='Cool Clothes Store'),
                 provider_class='sample',
             ),
        )
        self.api = API(import_log=self.log)
        self.api.dataset = copy.deepcopy(SAMPLE_DICT)
        self.api._product_image = '/dummy/path.jpeg'

    def tearDown(self):
        # FIXME: Remove local image if it exists
        fp = os.path.join(settings.MEDIA_ROOT, settings.APPAREL_PRODUCT_IMAGE_ROOT, 'cool-clothes-store', '__image.jpg')
        if os.path.exists(fp):
            os.remove(fp)

    def test_product_image_path(self):
        self.assertTrue(settings.APPAREL_PRODUCT_IMAGE_ROOT, 'APPAREL_PRODUCT_IMAGE_ROOT setting exists')
        self.assertEqual(
            self.api._product_image_path(self.api._get_first_product_image_path()),
            '%s/%s/%s/%s' % (
                settings.APPAREL_PRODUCT_IMAGE_ROOT,
                'cool-clothes-store',
                'whateverman',
                'a-cool-pair-of-jeans__c001.png',
            )
        )

    #@unittest.skip("Review this test")
    def test_product_image_no_url(self):
        self.assertRaises(IncompleteDataSet, self.api._product_image, None)

    def test_product_image(self):
        pass

        # FIXME: I cannot figure out how to connect to a test server and execute this test.
        #p = self.api.product_image()
        #
        #self.assertEqual(p, self.api.product_image_path, "Returns product_image_path property")
        #self.assertTrue(os.path.exists(os.path.join(settings.MEDIA_ROOT, p)), 'File downloaded')
        #

    #@unittest.skip("Review this test")
    def test_product_image_http_error(self):
        self.api.dataset['product']['image-url'] = 'http://www.hanssonlarsson.se/test/404.jpg'
        self.api._product_image = None

        try:
            # FIXME: assertRaises only works on callables
            self.api.product_image
        except SkipProduct:
            self.assertTrue(True, 'Require URL to exist')
        except Exception as e:
            self.fail('Require URL to exist, error was %s' % e.message)
        else:
            self.fail('Require URL to exist')

    '''def test_product_image_exists(self):
        target_file = os.path.join(
            settings.MEDIA_ROOT,
            self.api._product_image
        )
        shutil.copy(os.path.join(settings.STATIC_ROOT, '_test', '__image.png'), target_file)
        stat = os.stat(target_file)
        time.sleep(2) # Wait for time from

        p = self.api.product_image
        self.assertEqual(stat.st_mtime, os.stat(os.path.join(settings.MEDIA_ROOT, p)).st_mtime, 'File not change after downloading')'''

    def test_product_image_import(self):
        """
        Product image is downloaded during import
        """
        pass
        # FIXME: I cannot figure out how to connect to a test server and execute this test.

        #p = self.api.import_product()
        #self.assertTrue(os.path.exists(os.path.join(settings.MEDIA_ROOT, self.api.product_image_path)), 'Image downloaded during import')
        #self.assertEqual(p.product_image, self.api.product_image_path, 'image_path stored in product')


class TestDataSetImport(TransactionTestCase):
    def setUp(self):
        self.log = ImportLog.objects.create(
             vendor_feed=VendorFeed.objects.create(
                 name='testfeed',
                 url='http://example.com',
                 vendor=apparel.Vendor.objects.create(name='Cool Clothes Store'),
                 provider_class='sample',
             ),
        )
        self.api = API(import_log=self.log)
        self.dataset = copy.deepcopy(SAMPLE_DICT)
        self.api._product_image = '/dummy/path.jpeg'    # This prevent the tests from trying to download non-existant images

    def test_import_successful(self):
        """
        Tests if the import is successful using default valid dataset.
        This test is not ensuring all related data was created. See above tests for that.
        """
        self.api.dataset = self.dataset
        p = self.api.import_dataset()
        self.assertTrue(isinstance(p, apparel.Product), 'Data imported using default dataset')

    def test_import_successful_data(self):
        """
        Tests if the import is successful using valid dataset passed as a parameter.
        """
        p = self.api.import_dataset(data=self.dataset)
        self.assertTrue(isinstance(p, apparel.Product), 'Data using passed dataset')

    def test_import_validation(self):
        """
        Tests importation with no valid dataset.
        """
        self.dataset['version'] = 'xxx'
        self.assertRaises(ImporterError, self.api.import_dataset, self.dataset)

    def test_import_rollback(self):
        # TODO Understand the purpose of this test
        self.dataset['product']['manufacturer'] = None
        self.assertRaises(Exception, self.api.import_dataset, self.dataset)
        if apparel.Category.objects.count() > 0:
            self.fail('Objects not rolled back, are all product-related tables created with the InnoDB engine?')

    #@unittest.skip("Review this test")
    def test_import_dberror(self):
        # TODO Understand the purpose of this test
        self.dataset['product']['product-url'] = 'x' * 300
        self.assertRaises(ImporterError, self.api.import_dataset, self.dataset)


""" MAPPER """
class DummyDataMapper(DataMapper):
    def get_product_name(self):
        return self.record.get('name')

    def get_currency(self):
        raise SkipField('I do not care about this field')


class DummyProvider(Provider):
    pass


class MapperProcessTest(TestCase):
    def setUp(self):
        self.feed = VendorFeed.objects.create(
            vendor=apparel.Vendor.objects.create(name='My Vendor'),
            url='http://example.com/feed.csv',
            username='the username',
            password='the password',
            provider_class='DummyProvider',
        )
        self.feed.vendor = apparel.Vendor.objects.create(name='My Vendor')

        self.mapper = DataMapper(Mock(spec=DummyProvider(self.feed)))
        self.mapper.preprocess = Mock()
        self.mapper.postprocess = Mock()
        self.mapper.map_field = Mock()

    def test_translate(self):
        self.mapper.translate()
        self.assertTrue(self.mapper.preprocess.called, 'Called preprocess()')
        self.assertTrue(self.mapper.postprocess.called, 'Called postprocess()')
        '''self.assertEquals(
            self.mapper.map_field.call_args_list,
            [
                (('date',), {}),
                (('product-id',), {}),
                (('product-name',), {}),
                (('category',), {}),
                (('manufacturer',), {}),
                (('price',), {}),
                (('gender',), {}),
                (('currency',), {}),
                (('delivery-cost',), {}),
                (('delivery-time',), {}),
                (('image-url',), {}),
                (('product-url',), {}),
                (('description',), {}),
                (('availability',), {}),
                (('variations',), {}),
            ],
            'Called map_field() with each field'
        )'''


class FieldMapperTest(TestCase):
    def setUp(self):
        self.vendor = apparel.Vendor.objects.create(name='My Vendor')
        self.brand = apparel.Brand.objects.create(name='My Brand')
        self.feed = VendorFeed.objects.create(
            vendor= self.vendor,
            url='http://example.com/feed.csv',
            username='the username',
            password='the password',
            provider_class='DummyProvider',
        )
        self.mapper = DummyDataMapper(DummyProvider(self.feed), record={
            'product_id': 'the id',
            'name': 'the name',
            'product-url': 'the url',
            'price': 500,
            'description': """
                Some <b>funky</b> description<br/> containing
                HTML and n&aring;gra entities
            """,
            'manufacturer': self.brand.name
        })

    def test_map_field_record(self):
        self.assertEqual(self.mapper.map_field('product-url'), 'the url', 'Mapped field to data dict')
        self.assertEqual(self.mapper.map_field('product_url'), None, 'The - to / conversion does not apply to fields')

    def test_map_field_method(self):
        self.assertEqual(self.mapper.map_field('product-name'), 'the name')

    def test_map_field_nonexistent(self):
        self.assertEqual(self.mapper.map_field('some-field'), None)

    def test_map_field_skip(self):
        self.assertRaises(SkipField, self.mapper.map_field, 'currency')

    def test_map_fields(self):
        f = self.mapper.translate()
        self.assertTrue(isinstance(f, dict))
        self.assertTrue('product' in f)
        self.assertTrue('version' in f)
        self.assertTrue(re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z(?:.+?)?', f.get('date')))
        self.assertEqual(f['vendor'], 'My Vendor', 'Vendor name')

        p = f['product']

        self.assertFalse('currency' in p, 'SkipField is causing field to be ignored')
        self.assertEqual(p['delivery-time'], None, 'Missing field is filled with None value')
        self.assertEqual(p['variations'], [], 'variances defaults to empty array')

    def test_postprocess(self):
        f = self.mapper.translate()
        self.assertEqual(
            f['product']['description'],
            u'Some funky description containing\n HTML and n\xe5gra entities',
            'HTML stripped from description'
        )
        self.assertEqual(
            f['product']['price'],
            500,
            'Whitespaces stripped from all fields'
        )


class HelperMethodsTest(TestCase):
    def setUp(self):
        self.feed = VendorFeed.objects.create(
            vendor=apparel.Vendor.objects.create(name='My Vendor'),
            url='http://example.com/feed.csv',
            username='the username',
            password='the password',
            provider_class='DummyProvider',
        )
        self.mapper = DummyDataMapper(DummyProvider(self.feed), record={
            'product_id': 'the id',
            'name': 'the name',
            'product-url': 'the url',
        })

    def test_map_colors(self):
        c = self.mapper.map_colors(u'Here is a string with Black, navy and red')
        self.assertEqual(set(c), set((u'black', u'blue', u'red',)), 'Mapped colors')

    def test_trim(self):
        self.assertEqual(self.mapper.trim('   xxx xx xxx   '), 'xxx xx xxx', 'Trimmed leading and tailing whitespaces')
        self.assertEqual(self.mapper.trim('xxx xx xxx   '), 'xxx xx xxx', 'Trimmed tailing whitespaces')
        self.assertEqual(self.mapper.trim('   xxx xx xxx'), 'xxx xx xxx', 'Trimmed leading whitespaces')

    def test_trim_type(self):
        """
        Pass in anything to trim without it failing
        """

        self.assertEqual(self.mapper.trim(None),  None,  'Call trim() with None')
        self.assertEqual(self.mapper.trim(False), False, 'Call trim() with Boolean')
        self.assertEqual(self.mapper.trim(121),   121,   'Call trim() with intiger')
        self.assertEqual(self.mapper.trim(11.12), 11.12, 'Call trim() with float')

        self.assertEqual(self.mapper.trim(['  je h ', 'a   a a']), ['je h', 'a a a'], 'Call trim() with list of strings')
        self.assertEqual(self.mapper.trim([' ja a ', [' b ah']]), [' ja a ', [' b ah']], 'Call trim() with list of mixed data types')
        self.assertEqual(self.mapper.trim('  c c'), 'c c', 'Call trim() with string')
        self.assertEqual(self.mapper.trim({'a': 'A', 'b ': 'B '}), {'a': 'A', 'b ': 'B '}, 'Call trim() with dict')

    def test_strip_html(self):

        self.assertEqual(self.mapper.strip_html(u"""
            blah\n<p attr="value"
        >n&aring;got roligt
        </p>
        <b>&#160;hej&#x0046;</b>
        hej<br>d&aring;


            """),
            u'blah\n n\xe5got roligt\n \n \xa0hejF \n hej d\xe5',
            'Removed HTML and expanded entities'
        )


""" IMPORT """
class ImportLogTest(TestCase):
    def setUp(self):
        self.feed = VendorFeed.objects.create(
            name='myvendor',
            vendor=apparel.Vendor.objects.create(name='My Vendor'),
            url='http://example.com/feed.xml',
            provider_class='DummyProvider',
        )

    def test_defaults(self):
        log = ImportLog.objects.create(vendor_feed=self.feed)

        self.assertEqual(log.status, u'running', 'Status is running by default')
        self.assertEqual(log.end_time, None, 'No end_time set')
        self.assertEqual(self.feed.import_log.count(), 1, 'Added to VendorFeed')
        self.assertAlmostEqual(
            time.mktime(log.start_time.timetuple()),
            time.mktime(datetime.now().timetuple()),
            0,
            'start_time automatically set to now()'
        )

    def test_mark_complete(self):
        log = ImportLog.objects.create(vendor_feed=self.feed)

        log.status = 'completed'
        log.save()

        self.assertTrue(
            isinstance(log.end_time, datetime),
            'end_time updated if status set to complete'
        )

    def test_mark_failure(self):
        log = ImportLog.objects.create(vendor_feed=self.feed)
        log.status = 'failed'
        log.save()

        self.assertTrue(
            isinstance(log.end_time, datetime),
            'end_time updated if status set to failure'
        )

    def test_messages(self):
        log = ImportLog.objects.create(vendor_feed=self.feed)
        log.messages.create(message='Test 1')

        self.assertEquals(log.messages.count(), 1, 'Added one import log message')
        self.assertEquals(log.messages.all()[0].status, 'info', 'ImportLogMessage status defaults to info')
        self.assertTrue(isinstance(log.messages.all()[0].datetime, datetime), 'ImportLogMessage datetime set to now')


class VendorFeedTest(TestCase):
    def setUp(self):
        pass

    def test_import_log(self):
        feed = VendorFeed.objects.create(
            name='myvendor',
            vendor=apparel.Vendor.objects.create(name='Vendor'),
            url='http://example.com/feed.xml',
            provider_class='DummyProvider',
        )

        log = feed.import_log.create()
        self.assertEquals(feed, log.vendor_feed, 'Relationship OK')
        self.assertEquals(feed.import_log.count(), 1, 'Added ImportLog')

    def test_lastest_log(self):
        feed1 = VendorFeed.objects.create(
            name='vendor1',
            vendor=apparel.Vendor.objects.create(name='Vendor 1'),
            url='http://example.com/feed.xml',
            provider_class='DummyProvider',
        )
        feed2 = VendorFeed.objects.create(
            name='vendor2',
            vendor=apparel.Vendor.objects.create(name='Vendor 2'),
            url='http://example.com/feed.xml',
            provider_class='DummyProvider',
        )

        self.assertEquals(feed1.latest_import_log, None, 'No import logs available')

        log1 = feed1.import_log.create()
        self.assertEquals(feed1.latest_import_log, log1, 'Returns lastest log object')
        time.sleep(1)
        log2 = feed1.import_log.create()
        self.assertEquals(feed1.import_log.count(), 2, 'Two logs associated with feed')
        self.assertEquals(feed1.latest_import_log, log2, 'Only the latest returned by latest_log accessor')

        time.sleep(1)
        log3 = feed2.import_log.create()
        self.assertEquals(feed1.latest_import_log, log2, "Feed1's import log unchanged")
        self.assertEquals(feed2.latest_import_log, log3, "Feed2's import log correct")


""" PROVIDER """
class MyCSVProvider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(MyCSVProvider, self).__init__(*args, **kwargs)
        self.fieldnames = (
            'myfield1', 'myfield2', 'myfield3', 'myfield4', 'myfield5',
            'myfield6', 'myfield7', 'myfield8', 'myfield9', 'myfield10',
        )
        self.imported_data = []     # For testing only. All parsed and mapped data ends up here

    def import_data(self, data):
        self.imported_data.append(data)


class MyMapper(DataMapper):
    """
    This is a dummy mapper that just returns whatever it's been given to process
    """
    def translate(self):
        return self.record


# - Actual Test Cases -


class ProviderBaseTest(TestCase):
    """
    Tests basic functionality of the Provider class
    """
    def setUp(self):
        self.feed = VendorFeed.objects.create(
            vendor=apparel.Vendor.objects.create(name='My Vendor'),
            url='http://example.com/feed.csv',
            username='the username',
            password='the password',
            provider_class='DummyProvider',
        )
        self.test_date = date(2010, 9, 15)
        self._dummy_path = os.path.join(settings.APPAREL_IMPORTER_WAREHOUSE, 'my_vendor', '%s.csv' % self.test_date.strftime('%Y-%m-%d'))

        if not os.path.exists(os.path.split(self._dummy_path)[0]):
            os.makedirs(os.path.split(self._dummy_path)[0])

        # Write a dummy file to disk
        fh = open(self._dummy_path,'w')
        fh.write('one,two,three,four,five,six,seven,eight,nine,ten\n')
        fh.close()

    def tearDown(self):
        try:
            os.remove(self._dummy_path)
        except OSError:
            pass

    def test_create(self):
        p = Provider(self.feed)

        self.assertEquals(p.username, 'the username', 'Username set from feed')
        self.assertEquals(p.password, 'the password', 'password set from feed')
        self.assertEquals(p.url,      'http://example.com/feed.csv', 'URL set from feed')
        self.assertEquals(p.feed, self.feed, 'Reference to VendorFeed')
        self.assertEquals(p.file, None, 'file defaults to None')
        self.assertEquals(p.name, 'my_vendor', 'name constructed from vendor')
        self.assertEquals(p.extension, None, 'extension defaults to None')

        self.assertRaises(Exception, p.run)

    def test_load_provider(self):
        p = load_provider('sample', self.feed)

        self.assertTrue(isinstance(p, Provider), 'Provider extends Provider')

    def test_fetch_warehouse(self):
        p = load_provider('sample', self.feed)
        p.fetch(from_warehouse=True, for_date=self.test_date)

        self.assertTrue(os.path.exists(self._dummy_path), 'Warehouse directory created when needed')
        self.assertTrue(isinstance(p.file, file), 'File object assiged to Proivider')
        self.assertTrue(p.file.closed is False, 'File object is opened')
        self.assertEqual(p.file.mode, 'r', 'File object is opened for reading')


class CSVProviderTest(TestCase):
    def setUp(self):
        self.feed = VendorFeed.objects.create(
            vendor=apparel.Vendor.objects.create(name='My Vendor'),
            url='http://example.com/feed.csv',
            username='the username',
            password='the password',
            provider_class='DummyProvider',
        )
        self.test_date = date(2010, 9, 15)
        self._dummy_path = os.path.join(settings.APPAREL_IMPORTER_WAREHOUSE, 'my_vendor', '%s.csv' % self.test_date.strftime('%Y-%m-%d'))

        if not os.path.exists(os.path.split(self._dummy_path)[0]):
            os.makedirs(os.path.split(self._dummy_path)[0])

        # Write a dummy file to disk
        fh = open(self._dummy_path,'w')
        fh.write('one,two,three,four,five,six,seven,eight,nine,ten\n')
        fh.close()

    def tearDown(self):
        try:
            os.remove(self._dummy_path)
        except OSError:
            pass

    def test_csv_class(self):
        p = MyCSVProvider(self.feed)

        self.assertEquals(p.extension, 'csv', 'Extension defaults to CSV')
        self.assertEquals(p.dialect, None, 'There is a dialect property')

    def test_csv_parsing(self):
        p = MyCSVProvider(self.feed)
        p.mapper = MyMapper

        # FIXME: Why isn't there an inverse assertRaises?
        try:
            p.run(from_warehouse=True, for_date=self.test_date)
        except Exception, e:
            print e
            self.fail('Parse CSV file')
        else:
            self.assertTrue(True, 'Parsed and imported CSV file')

        self.assertEquals(
            p.imported_data,
            [{'myfield1': u'one',
             'myfield10': u'ten',
             'myfield2': u'two',
             'myfield3': u'three',
             'myfield4': u'four',
             'myfield5': u'five',
             'myfield6': u'six',
             'myfield7': u'seven',
             'myfield8': u'eight',
             'myfield9': u'nine'}],
            'Parsed data given to mapper'
        )