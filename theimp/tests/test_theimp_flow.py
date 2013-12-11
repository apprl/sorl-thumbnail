import json
from collections import deque

from django.conf import settings
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.db.models.loading import get_model

from theimp.parser import Parser
from theimp.importer import Importer


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
                'description': 'Product Name description',
                'gender': 'female products',
                'currency': 'SEK',
                'regular_price': '999.99',
                'discount_price': '879.99',
                'in_stock': True,
                'image_urls': ['http://example.com/image.jpg'],
                'images': [{'checksum': 'abc',
                            'path': 'image.jpg',
                            'url': 'http://example.com/image.jpg'}],

            }
        }
        json_data = json.dumps(data)
        product = self.product_model.objects.create(key=key, json=json_data, vendor=self.vendor)
        self.assertTrue(product.pk)
        self.parse_queue.put(product.pk)

        # Parse
        parser = Parser(parse_queue=self.parse_queue, site_queue=self.site_queue)
        parser.run()

        product = self.product_model.objects.get(key=key)
        self.assertTrue(product.is_auto_validated)

        # Site import (add)
        importer = Importer(site_queue=self.site_queue)
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertTrue(site_product)

        # Parse again
        self.parse_queue.put(product.pk)

        parser = Parser(parse_queue=self.parse_queue, site_queue=self.site_queue)
        parser.run()

        product = self.product_model.objects.get(key=key)
        self.assertTrue(product.is_auto_validated)

        # Site import (update)
        importer = Importer(site_queue=self.site_queue)
        importer.run()

        site_product = self.site_product_model.objects.get(slug='fifth-avenue-shoe-repair-product-name')
        self.assertTrue(site_product)
