import json
import unittest

from mock import patch, Mock

from django.conf import settings
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.db.models.loading import get_model

from theimp.parser import Parser
from theimp.importer import Importer
from theimp.utils import ProductItem


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TheimpFlowTest(TransactionTestCase):
    fixtures = ['initial.json']

    def setUp(self):
        self.product_model = get_model('theimp', 'Product')
        self.site_product_model = get_model('apparel', 'Product')

        # Create option types for site
        get_model('apparel', 'OptionType').objects.create(name='color')
        get_model('apparel', 'OptionType').objects.create(name='pattern')

        # Setup vendor for site and importer
        self.site_vendor = get_model('apparel', 'Vendor').objects.create(name='Fifth Avenue Shoe Repair')
        self.vendor = get_model('theimp', 'Vendor').objects.create(name='TestVendor', vendor=self.site_vendor, affiliate_identifier='fifth_avenue')

        # Setup category and brand mapping
        self.imported_brand = get_model('apparel', 'Brand').objects.create(name='Fifth Avenue Shoe Repair')
        self.imported_category = get_model('apparel', 'Category').objects.create(name='Category')
        get_model('theimp', 'BrandMapping').objects.create(vendor=self.vendor, brand='Fifth Avenue', mapped_brand=self.imported_brand)
        get_model('theimp', 'CategoryMapping').objects.create(vendor=self.vendor, category='scraped-category', mapped_category=self.imported_category)

    @patch('theimp.parser.logger')
    def test_parser_parse_with_none_product(self, mock_logger):
        parser = Parser()
        parser.parse(None)

        mock_logger.error.assert_called_with('Could not parse invalid product')
        self.assertEqual(self.product_model.objects.count(), 0)

    def test_find_site_product_fail(self):
        data = {'site_product': 10000}
        product = self.product_model.objects.create(key='temp', json=json.dumps(data), vendor=self.vendor)
        item = ProductItem(product)

        self.assertEqual(item.get_site_product(), 10000)

        importer = Importer()
        importer._find_site_product(item)

        self.assertEqual(item.get_site_product(), None)

    def test_product_options(self):
        product = self.site_product_model.objects.create(product_name='Product Name')

        def get_final_side_effect(*args, **kwargs):
            if args[0] == 'colors':
                return ['red', 'blue']
            elif args[0] == 'patterns':
                return ['striped']
            return None

        mock_item = Mock()
        mock_item.get_final.side_effect = get_final_side_effect

        self.assertEqual(mock_item.get_final('colors'), ['red', 'blue'])

        importer = Importer()
        importer._update_product_options(mock_item, product)

        product = self.site_product_model.objects.get(product_name='Product Name')
        self.assertEqual(product.options.count(), 3)
        self.assertEqual(sorted(list(product.colors)), sorted([u'red', u'blue']))
        self.assertEqual(sorted(list(product.options.filter(option_type__name='pattern').values_list('value', flat=True))), sorted([u'striped']))


    @patch('theimp.importer.logger')
    @unittest.skip("Review this test")
    def test_flow(self, mock_logger):
        # Create a product from scraped data
        key = 'http://example.com/product/product-name.html'
        data = {
            'final': {},
            'parsed': {},
            'scraped': {
                'key': key,
                'url': key,
                'sku': '1234ABCD',
                'affiliate': 'linkshare',
                'name': 'Product Name',
                'brand': 'Fifth Avenue',
                'category': 'scraped-category',
                'vendor': 'TestVendor',
                'description': 'Product Name description  ',
                'gender': 'female products',
                'colors': 'red',
                'currency': 'SEK',
                'regular_price': '999.99',
                'discount_price': '879.99',
                'in_stock': True,
                'image_urls': ['http://example.com/image_not_available.jpg'],
                'images': [{'checksum': 'abc',
                            'path': 'image_not_available.jpg',
                            'url': 'http://example.com/image_not_available.jpg'}],

            }
        }
        json_data = json.dumps(data)
        product = self.product_model.objects.create(key=key, json=json_data, vendor=self.vendor)
        self.assertEqual(product.is_dropped, False)

        #
        # 1. Initial parse and import
        #

        # Parse
        parser = Parser()
        parser.parse(product)

        product = self.product_model.objects.get(key=key)
        self.assertTrue(product.is_validated)

        # Site import (add)
        importer = Importer()
        importer.run()

        self.assertFalse(mock_logger.exception.called)

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Name')
        self.assertEqual(site_product.description, 'Product Name description')
        self.assertEqual(site_product.availability, True)
        self.assertEqual(site_product.manufacturer.name, 'Fifth Avenue Shoe Repair')
        self.assertEqual(site_product.category.name, 'Category')
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertIsNotNone(site_product.default_vendor)
        self.assertEqual(site_product.default_vendor.buy_url, 'http://example.com/product/product-name.html')

        #
        # 2. Parse and import again
        #

        # Parse and import again (update)
        parser = Parser()
        parser.parse(product)
        importer = Importer()
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Name')
        self.assertEqual(site_product.description, 'Product Name description')
        self.assertEqual(site_product.availability, True)
        self.assertEqual(site_product.manufacturer.name, 'Fifth Avenue Shoe Repair')
        self.assertEqual(site_product.category.name, 'Category')
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertIsNotNone(site_product.default_vendor)
        self.assertEqual(site_product.default_vendor.buy_url, 'http://example.com/product/product-name.html')

        #
        # 3. Parse invalid data and import again
        #

        # Mark product json with invalid data and try to parse and import it again
        product = self.product_model.objects.get(key=key)
        product_json = json.loads(product.json)
        product_json['scraped']['currency'] = ''
        product.json = json.dumps(product_json)
        product.save()

        parser = Parser()
        parser.parse(product)
        importer = Importer()
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Name')
        self.assertEqual(site_product.description, 'Product Name description')
        self.assertEqual(site_product.availability, False)
        self.assertEqual(site_product.manufacturer.name, 'Fifth Avenue Shoe Repair')
        self.assertEqual(site_product.category.name, 'Category')
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertIsNotNone(site_product.default_vendor)
        self.assertEqual(site_product.default_vendor.buy_url, 'http://example.com/product/product-name.html')

        #
        # 4. Parse changed product name and import again
        #

        product = self.product_model.objects.get(key=key)
        product_json = json.loads(product.json)
        product_json['scraped']['currency'] = 'SEK'
        product_json['scraped']['name'] = 'Product Correct Name'
        product.json = json.dumps(product_json)
        product.save()


        parser = Parser()
        parser.parse(product)
        importer = Importer()
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Correct Name')
        self.assertEqual(site_product.description, 'Product Name description')
        self.assertEqual(site_product.availability, True)
        self.assertEqual(site_product.manufacturer.name, 'Fifth Avenue Shoe Repair')
        self.assertEqual(site_product.category.name, 'Category')
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertIsNotNone(site_product.default_vendor)
        self.assertEqual(site_product.default_vendor.buy_url, 'http://example.com/product/product-name.html')

        #
        # 5. Manual update and parse and import again
        #

        product = self.product_model.objects.get(key=key)
        product_json = json.loads(product.json)
        product_json['manual'] = {'description': 'Our manual description written by our team.'}
        product.json = json.dumps(product_json)
        product.save()

        parser = Parser()
        parser.parse(product)
        importer = Importer()
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Correct Name')
        self.assertEqual(site_product.description, 'Our manual description written by our team.')
        self.assertEqual(site_product.availability, True)
        self.assertEqual(site_product.manufacturer.name, 'Fifth Avenue Shoe Repair')
        self.assertEqual(site_product.category.name, 'Category')
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertIsNotNone(site_product.default_vendor)
        self.assertEqual(site_product.default_vendor.buy_url, 'http://example.com/product/product-name.html')

        #
        # 6. Mark product as dropped
        #

        product = self.product_model.objects.get(key=key)
        product.is_dropped = True
        product.save()

        parser = Parser()
        parser.parse(product)

        product = self.product_model.objects.get(key=key)
        self.assertFalse(product.is_validated)

        importer = Importer()
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Correct Name')
        self.assertEqual(site_product.description, 'Our manual description written by our team.')
        self.assertEqual(site_product.availability, False)


    @patch('theimp.importer.logger')
    @unittest.skip("Review this test")
    def test_find_site_product_flow(self, mock_logger):
        key = 'http://example.com/product/product-name.html'
        json_data = json.dumps({
            'final': {},
            'parsed': {},
            'scraped': {
                'key': key,
                'url': key,
                'sku': '1234ABCD',
                'affiliate': 'aan',
                'name': 'Product Name',
                'brand': 'Fifth Avenue',
                'category': 'scraped-category',
                'vendor': 'TestVendor',
                'description': 'Product Name description  ',
                'gender': 'female products',
                'colors': 'red',
                'currency': 'SEK',
                'regular_price': '999.99',
                'discount_price': '879.99',
                'in_stock': True,
                'image_urls': ['http://example.com/image_not_available.jpg'],
                'images': [{'checksum': 'abc',
                            'path': 'image_not_available.jpg',
                            'url': 'http://example.com/image_not_available.jpg'}],

            }
        })
        product = self.product_model.objects.create(key=key, json=json_data, vendor=self.vendor)

        parser = Parser()
        parser.parse(product)
        importer = Importer()
        importer.run()

        self.assertFalse(mock_logger.exception.called)

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Name')
        self.assertEqual(site_product.description, 'Product Name description')
        self.assertEqual(site_product.availability, True)
        self.assertEqual(site_product.manufacturer.name, 'Fifth Avenue Shoe Repair')
        self.assertEqual(site_product.category.name, 'Category')
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertIsNotNone(site_product.default_vendor)
        self.assertEqual(site_product.default_vendor.buy_url, 'http://example.com/product/product-name.html')

        # Update slug
        site_product.slug = 'fifth-avenue-shoe-repair-product-name-10'
        site_product.save()

        # Product changes description
        product = self.product_model.objects.get(key=key)
        product_json = json.loads(product.json)
        product_json['manual'] = {'description': 'Our manual description written by our team.'}
        product.json = json.dumps(product_json)
        product.save()

        # Parse and import product
        parser = Parser()
        parser.parse(product)
        importer = Importer()
        importer.run()

        # Verify that description is now updated with a changed slug
        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name-10')
        self.assertEqual(site_product.description, 'Our manual description written by our team.')
