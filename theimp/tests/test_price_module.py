"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase

from theimp.parser.modules.price import Price

class PriceModuleTest(TestCase):

    def setUp(self):
        self.module = Price(None)

    def test_price(self):
        parsed_item = self.module({'price': '1234', 'currency': 'SEK'}, {}, 0)

        self.assertEqual(parsed_item['regular_price'], '1234')
        self.assertEqual(parsed_item['is_discount'], False)
        self.assertEqual(parsed_item['currency'], 'SEK')
        self.assertNotIn('discount_price', parsed_item)

    def test_regular_price(self):
        parsed_item = self.module({'regular_price': '1234', 'currency': 'SEK'}, {}, 0)

        self.assertEqual(parsed_item['regular_price'], '1234')
        self.assertEqual(parsed_item['is_discount'], False)
        self.assertEqual(parsed_item['currency'], 'SEK')
        self.assertNotIn('discount_price', parsed_item)

    def test_price_with_space(self):
        parsed_item = self.module({'price': '1 234', 'currency': 'SEK'}, {}, 0)

        self.assertEqual(parsed_item['regular_price'], '1234')
        self.assertEqual(parsed_item['is_discount'], False)
        self.assertEqual(parsed_item['currency'], 'SEK')
        self.assertNotIn('discount_price', parsed_item)

    def test_invalid_price_value(self):
        parsed_item = self.module({'price': 'invalid', 'currency': 'SEK'}, {}, 0)

        self.assertEqual(parsed_item, {})

    def test_invalid_price_and_currency(self):
        parsed_item = self.module({'price': 'invalid', 'currency': 'invalid'}, {}, 0)

        self.assertEqual(parsed_item, {})

    def test_discount_price(self):
        parsed_item = self.module({'regular_price': '1234', 'discount_price': '1000', 'currency': 'SEK'}, {}, 0)

        self.assertEqual(parsed_item['regular_price'], '1234')
        self.assertEqual(parsed_item['discount_price'], '1000')
        self.assertEqual(parsed_item['currency'], 'SEK')
        self.assertEqual(parsed_item['is_discount'], True)

    def test_missing_currency(self):
        parsed_item = self.module({'price': '1 234', 'currency': ''}, {}, 0)

        self.assertEqual(parsed_item, {})

    def test_invalid_currency(self):
        parsed_item = self.module({'price': '1 234', 'currency': 'Kronor'}, {}, 0)

        self.assertEqual(parsed_item, {})

    def test_discount_higher_then_regular(self):
        parsed_item = self.module({'price': '1 355', 'discount_price': '1999', 'currency': 'SEK'}, {}, 0)

        self.assertEqual(parsed_item, {})

    def test_regular_price_and_discount_price_in_price_variable(self):
        parsed_item = self.module({'price': '1 399', 'regular_price': '1 599', 'currency': 'EUR'}, {}, 0)

        self.assertEqual(parsed_item.get('currency'), 'EUR')
        self.assertEqual(parsed_item.get('regular_price'), '1599')
        self.assertEqual(parsed_item.get('discount_price'), '1399')
        self.assertEqual(parsed_item.get('is_discount'), True)

