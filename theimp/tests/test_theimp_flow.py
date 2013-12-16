import json
from collections import deque

from mock import patch, Mock

from django.conf import settings
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.db.models.loading import get_model

from theimp.parser import Parser
from theimp.importer import Importer
from theimp.utils import ProductItem


class HotQueueMock(object):

    queues = {}

    def __init__(self, queue_name, *args, **kwargs):
        if queue_name not in HotQueueMock.queues:
            HotQueueMock.queues[queue_name] = deque()

        self.queue = HotQueueMock.queues[queue_name]

    def consume(self):
        try:
            while True:
                yield self.queue.popleft()
        except:
            pass

    def put(self, item):
        self.queue.append(item)


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TheimpFlowTest(TransactionTestCase):
    fixtures = ['initial.json']

    def setUp(self):
        self.product_model = get_model('theimp', 'Product')
        self.vendor_model = get_model('theimp', 'Vendor')
        self.brand_mapper_model = get_model('theimp', 'BrandMapping')
        self.category_mapper_model = get_model('theimp', 'CategoryMapping')
        self.site_product_model = get_model('apparel', 'Product')
        self.site_vendor_model = get_model('apparel', 'Vendor')
        self.site_brand_model = get_model('apparel', 'Brand')
        self.site_category_model = get_model('apparel', 'Category')

        # Create option types for site
        get_model('apparel', 'OptionType').objects.create(name='color')
        get_model('apparel', 'OptionType').objects.create(name='pattern')

        self.parse_queue = HotQueueMock(settings.THEIMP_QUEUE_PARSE)
        self.site_queue = HotQueueMock(settings.THEIMP_QUEUE_SITE)

        self.category = self.site_category_model.objects.create(name='Category',
                                                                name_en='Category',
                                                                name_sv='Category',
                                                                name_da='Category',
                                                                name_no='Category',
                                                                name_order_en='A',
                                                                name_order_sv='A',
                                                                name_order_da='A',
                                                                name_order_no='A')
        self.brand = self.site_brand_model.objects.create(name='Fifth Avenue Shoe Repair')
        self.site_vendor = self.site_vendor_model.objects.create(name='Fifth Avenue Shoe Repair')
        self.vendor = self.vendor_model.objects.create(name='TestVendor',
                                                       vendor=self.site_vendor,
                                                       affiliate_identifier='fifth_avenue')
        self.brand_mapper_model.objects.create(vendor=self.vendor,
                                               brand='Fifth Avenue',
                                               mapped_brand=self.brand)
        self.category_mapper_model.objects.create(vendor=self.vendor,
                                                  category='scraped-category',
                                                  mapped_category=self.category)

    @patch('theimp.parser.logger')
    def test_parser_queue(self, mock_logger):
        self.parse_queue.put(1)
        parser = Parser(parse_queue=self.parse_queue, site_queue=self.site_queue)
        parser.run()

        mock_logger.exception.assert_called_with('Could not load product with id 1')
        self.assertEqual(self.product_model.objects.count(), 0)

    @patch('theimp.importer.logger')
    def test_importer_queue(self, mock_logger):
        self.site_queue.put((1, True))
        importer = Importer(site_queue=self.site_queue)
        importer.run()

        mock_logger.exception.assert_called_with('Could not load product with id 1')
        self.assertEqual(self.site_product_model.objects.count(), 0)

    def test_find_site_product_fail(self):
        data = {'site_product': 10000}
        product = self.product_model.objects.create(key='temp', json=json.dumps(data), vendor=self.vendor)
        item = ProductItem(product)

        self.assertEqual(item.get_site_product(), 10000)

        importer = Importer(site_queue=Mock())
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

        importer = Importer(site_queue=Mock())
        importer._update_product_options(mock_item, product)

        product = self.site_product_model.objects.get(product_name='Product Name')
        self.assertEqual(product.options.count(), 3)
        self.assertEqual(sorted(list(product.colors)), sorted([u'red', u'blue']))
        self.assertEqual(sorted(list(product.options.filter(option_type__name='pattern').values_list('value', flat=True))), sorted([u'striped']))

    def test_flow(self):
        # Create a product from scraped data
        key = 'http://example.com/product/product-name.html'
        data = {
            'final': {},
            'parsed': {},
            'scraped': {
                'key': key,
                'url': key,
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
        }
        json_data = json.dumps(data)
        product = self.product_model.objects.create(key=key, json=json_data, vendor=self.vendor)
        self.assertEqual(product.dropped, False)

        #
        # 1. Initial parse and import
        #

        # Parse
        self.parse_queue.put(product.pk)
        parser = Parser(parse_queue=self.parse_queue, site_queue=self.site_queue)
        parser.run()

        product = self.product_model.objects.get(key=key)
        self.assertTrue(product.is_auto_validated)

        # Site import (add)
        importer = Importer(site_queue=self.site_queue)
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Name')
        self.assertEqual(site_product.description, 'Product Name description')
        self.assertEqual(site_product.availability, True)
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertTrue(site_product.default_vendor)

        #
        # 2. Parse and import again
        #

        # Parse and import again (update)
        self.parse_queue.put(product.pk)
        parser = Parser(parse_queue=self.parse_queue, site_queue=self.site_queue)
        parser.run()
        importer = Importer(site_queue=self.site_queue)
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Name')
        self.assertEqual(site_product.description, 'Product Name description')
        self.assertEqual(site_product.availability, True)
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertTrue(site_product.default_vendor)

        #
        # 3. Parse invalid data and import again
        #

        # Mark product json with invalid data and try to parse and import it again
        product = self.product_model.objects.get(key=key)
        product_json = json.loads(product.json)
        product_json['scraped']['currency'] = ''
        product.json = json.dumps(product_json)
        product.save()

        self.parse_queue.put(product.pk)
        parser = Parser(parse_queue=self.parse_queue, site_queue=self.site_queue)
        parser.run()
        importer = Importer(site_queue=self.site_queue)
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Name')
        self.assertEqual(site_product.description, 'Product Name description')
        self.assertEqual(site_product.availability, False)
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertTrue(site_product.default_vendor)

        #
        # 4. Parse changed product name and import again
        #

        product = self.product_model.objects.get(key=key)
        product_json = json.loads(product.json)
        product_json['scraped']['currency'] = 'SEK'
        product_json['scraped']['name'] = 'Product Correct Name'
        product.json = json.dumps(product_json)
        product.save()

        self.parse_queue.put(product.pk)
        parser = Parser(parse_queue=self.parse_queue, site_queue=self.site_queue)
        parser.run()
        importer = Importer(site_queue=self.site_queue)
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Correct Name')
        self.assertEqual(site_product.description, 'Product Name description')
        self.assertEqual(site_product.availability, True)
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertTrue(site_product.default_vendor)

        #
        # 5. Manual update and parse and import again
        #

        product = self.product_model.objects.get(key=key)
        product_json = json.loads(product.json)
        product_json['manual'] = {'description': 'Our manual description written by our team.'}
        product.json = json.dumps(product_json)
        product.save()

        self.parse_queue.put(product.pk)
        parser = Parser(parse_queue=self.parse_queue, site_queue=self.site_queue)
        parser.run()
        importer = Importer(site_queue=self.site_queue)
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertEqual(site_product.product_name, 'Product Correct Name')
        self.assertEqual(site_product.description, 'Our manual description written by our team.')
        self.assertEqual(site_product.availability, True)
        self.assertEqual(list(site_product.colors), ['red'])
        self.assertTrue(site_product.default_vendor)
