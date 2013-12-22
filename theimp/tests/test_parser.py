import json

from mock import Mock, MagicMock, PropertyMock

from django.conf import settings
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.db.models.loading import get_model

from theimp.parser import Parser
from theimp.utils import ProductItem


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TheimpFlowTest(TransactionTestCase):
    fixtures = ['initial.json']

    def setUp(self):
        pass

    def test_initial_parse_method_nothing_scraped(self):
        product_mock = MagicMock()
        product_mock_json = PropertyMock(return_value=json.dumps({'scraped': {}, 'parsed': {}}))
        type(product_mock).json = product_mock_json

        item = ProductItem(product_mock)
        parser = Parser(parse_queue=Mock(), site_queue=Mock())
        item = parser.initial_parse(item)

        self.assertEqual(item.data[ProductItem.KEY_PARSED], {})

    def test_initial_parse_method_none_values(self):
        product_mock = MagicMock()
        product_mock_json = PropertyMock(return_value=json.dumps({'scraped': {'name': None, 'description': None, 'vendor_id': None, 'affiliate': None, 'in_stock': None, 'images': None}, 'parsed': {}}))
        type(product_mock).json = product_mock_json

        item = ProductItem(product_mock)
        parser = Parser(parse_queue=Mock(), site_queue=Mock())
        item = parser.initial_parse(item)

        self.assertEqual(item.data[ProductItem.KEY_PARSED], {})

    def test_clear_final_layer_before_finalization(self):
        key = 'http://example.com/product/product-name.html'
        data = {
            'final': {'patterns': 'striped'},
            'scraped': {},
            'parsed': {
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

        product_mock = MagicMock()
        product_mock_json = PropertyMock(return_value=json.dumps(data))
        type(product_mock).json = product_mock_json

        item = ProductItem(product_mock)
        parser = Parser(parse_queue=Mock(), site_queue=Mock())

        new_item = parser.finalize(item, True)
        self.assertIsNone(new_item.get_final('patterns'))
        self.assertEqual(new_item.get_final('colors'), 'red')
