from django.test import TestCase

from theimp.parser.modules.price import Price

class PriceModuleTest(TestCase):

    def setUp(self):
        self.module = Price(None)

    def test_price(self):
        parsed_item = self.module({'price': '1234', 'currency': 'SEK'}, {}, None)

        self.assertEqual(parsed_item['regular_price'], '1234')
        self.assertEqual(parsed_item['is_discount'], False)
        self.assertEqual(parsed_item['currency'], 'SEK')
        self.assertNotIn('discount_price', parsed_item)

    def test_regular_price(self):
        parsed_item = self.module({'regular_price': '1234', 'currency': 'SEK'}, {}, None)

        self.assertEqual(parsed_item['regular_price'], '1234')
        self.assertEqual(parsed_item['is_discount'], False)
        self.assertEqual(parsed_item['currency'], 'SEK')
        self.assertNotIn('discount_price', parsed_item)

    def test_price_with_space(self):
        parsed_item = self.module({'price': '1 234', 'currency': 'SEK'}, {}, None)

        self.assertEqual(parsed_item['regular_price'], '1234')
        self.assertEqual(parsed_item['is_discount'], False)
        self.assertEqual(parsed_item['currency'], 'SEK')
        self.assertNotIn('discount_price', parsed_item)

    def test_invalid_price_value(self):
        parsed_item = self.module({'price': 'invalid', 'currency': 'SEK'}, {}, None)

        self.assertEqual(parsed_item, {})

    def test_invalid_price_and_currency(self):
        parsed_item = self.module({'price': 'invalid', 'currency': 'invalid'}, {}, None)

        self.assertEqual(parsed_item, {})

    def test_discount_price(self):
        parsed_item = self.module({'regular_price': '1234', 'discount_price': '1000', 'currency': 'SEK'}, {}, None)

        self.assertEqual(parsed_item['regular_price'], '1234')
        self.assertEqual(parsed_item['discount_price'], '1000')
        self.assertEqual(parsed_item['currency'], 'SEK')
        self.assertEqual(parsed_item['is_discount'], True)

    def test_missing_currency_field(self):
        parsed_item = self.module({'price': '1234'}, {}, None)

        self.assertEqual(parsed_item, {})

    def test_missing_currency_value(self):
        parsed_item = self.module({'price': '1 234', 'currency': ''}, {}, None)

        self.assertEqual(parsed_item, {})

    def test_invalid_currency(self):
        parsed_item = self.module({'price': '1 234', 'currency': 'Kronor'}, {}, None)

        self.assertEqual(parsed_item, {})

    def test_discount_higher_then_regular(self):
        parsed_item = self.module({'price': '1 355', 'discount_price': '1999', 'currency': 'SEK'}, {}, None)

        self.assertEqual(parsed_item, {})

    def test_regular_price_and_discount_price_in_price_variable(self):
        parsed_item = self.module({'price': '1 399', 'regular_price': '1 599', 'currency': 'EUR'}, {}, None)

        self.assertEqual(parsed_item.get('currency'), 'EUR')
        self.assertEqual(parsed_item.get('regular_price'), '1599')
        self.assertEqual(parsed_item.get('discount_price'), '1399')
        self.assertEqual(parsed_item.get('is_discount'), True)

    def test_fifth_avenue_price(self):
        parsed_item = self.module({'regular_price': '3495', 'discount_price': '1747.50', 'currency': 'SEK'}, {}, None)

        self.assertEqual(parsed_item.get('currency'), 'SEK')
        self.assertEqual(parsed_item.get('regular_price'), '3495')
        self.assertEqual(parsed_item.get('discount_price'), '1747.50')
        self.assertEqual(parsed_item.get('is_discount'), True)

    def test_regular_and_discount_price_is_equal(self):
        parsed_item = self.module({'regular_price': '219', 'discount_price': '219', 'currency': 'SEK'}, {}, None)
        self.assertEqual(parsed_item.get('currency'), 'SEK')
        self.assertEqual(parsed_item.get('regular_price'), '219')
        self.assertEqual(parsed_item.get('discount_price'), None)
        self.assertEqual(parsed_item.get('is_discount'), False)

    def test_regular_and_discount_price_is_equal_previous_value(self):
        parsed_item = self.module({'regular_price': '219', 'discount_price': '219', 'currency': 'SEK'}, {'is_discount': True, 'discount_price': '219'}, None)
        self.assertEqual(parsed_item.get('currency'), 'SEK')
        self.assertEqual(parsed_item.get('regular_price'), '219')
        self.assertEqual(parsed_item.get('discount_price'), None)
        self.assertEqual(parsed_item.get('is_discount'), False)
