# -*- coding: utf-8 -*-
from decimal import Decimal

from django.test import TestCase

try:

    from spiderpig.spidercrawl.pipelines import PricePipeline
except ImportError:
    from spiderpig.pipelines import PricePipeline

class SpiderpigPricePipelineTest(TestCase):

    def setUp(self):
        self.pipeline = PricePipeline()

    def test_empty(self):
        self.assertEqual(self.pipeline.parse_price(''), (None, None))
        self.assertEqual(self.pipeline.parse_price(u''), (None, None))
        self.assertEqual(self.pipeline.parse_price(None), (None, None))

    def test_price(self):
        self.assertEqual(self.pipeline.parse_price('1 299'), (Decimal('1299'), None))
        self.assertEqual(self.pipeline.parse_price('100.99'), (Decimal('100.99'), None))
        self.assertEqual(self.pipeline.parse_price('100,99'), (Decimal('100.99'), None))
        self.assertEqual(self.pipeline.parse_price('1,000.99'), (Decimal('1000.99'), None))
        self.assertEqual(self.pipeline.parse_price('1 234 567.89'), (Decimal('1234567.89'), None))
        self.assertEqual(self.pipeline.parse_price('1,234,567.89'), (Decimal('1234567.89'), None))
        self.assertEqual(self.pipeline.parse_price('12,34,567.89'), (Decimal('1234567.89'), None))
        self.assertEqual(self.pipeline.parse_price('1 234 567,89'), (Decimal('1234567.89'), None))
        self.assertEqual(self.pipeline.parse_price('1.234.567,89'), (Decimal('1234567.89'), None))

    def test_price_and_currency(self):
        self.assertEqual(self.pipeline.parse_price('1299 SEK'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('1 299 SEK'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('1,299 SEK'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('1,299.99 SEK'), (Decimal('1299.99'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('1.299,99 SEK'), (Decimal('1299.99'), 'SEK'))

        self.assertEqual(self.pipeline.parse_price('SEK 1299'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('SEK 1 299'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('SEK 1,299'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('SEK 1,299.99'), (Decimal('1299.99'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('SEK 1.299,99'), (Decimal('1299.99'), 'SEK'))

        self.assertEqual(self.pipeline.parse_price('SEK1299'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('SEK1 299'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('SEK1,299'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('SEK1,299.99'), (Decimal('1299.99'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('SEK1.299,99'), (Decimal('1299.99'), 'SEK'))

        self.assertEqual(self.pipeline.parse_price('1299SEK'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('1 299SEK'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('1,299SEK'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('1,299.99SEK'), (Decimal('1299.99'), 'SEK'))
        #self.assertEqual(self.pipeline.parse_price('1.299,99SEK'), (Decimal('1299.99'), 'SEK'))

    def test_price_and_non_standard_currency(self):
        self.assertEqual(self.pipeline.parse_price(u'1299 kr'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price(u'1299kr'), (Decimal('1299'), 'SEK'))

        self.assertEqual(self.pipeline.parse_price(u'kr 1299'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price(u'kr1299'), (Decimal('1299'), 'SEK'))

    def test_price_and_unicode_currency(self):
        self.assertEqual(self.pipeline.parse_price(u'€1299'), (Decimal('1299'), 'EUR'))
        self.assertEqual(self.pipeline.parse_price(u'€ 1299'), (Decimal('1299'), 'EUR'))

        self.assertEqual(self.pipeline.parse_price(u'$1299'), (Decimal('1299'), 'USD'))
        self.assertEqual(self.pipeline.parse_price(u'$ 1299'), (Decimal('1299'), 'USD'))

        self.assertEqual(self.pipeline.parse_price(u'£1299'), (Decimal('1299'), 'GBP'))
        self.assertEqual(self.pipeline.parse_price(u'£ 1299'), (Decimal('1299'), 'GBP'))

        self.assertEqual(self.pipeline.parse_price(u'US$1299'), (Decimal('1299'), 'USD'))
        self.assertEqual(self.pipeline.parse_price(u'US$ 1299'), (Decimal('1299'), 'USD'))

    def test_only_currency(self):
        self.assertEqual(self.pipeline.parse_price('SEK'), (None, None))

    def test_extra_chars(self):
        self.assertEqual(self.pipeline.parse_price('(1299 SEK)'), (Decimal('1299'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price('[ 1 299.99 SEK ]'), (Decimal('1299.99'), 'SEK'))

    def test_oki_ni_price(self):
        self.assertEqual(self.pipeline.parse_price(u'\xa3149.00'), (Decimal('149'), 'GBP'))

    def test_fifth_avenue_price(self):
        self.assertEqual(self.pipeline.parse_price(u'3495 SEK'), (Decimal('3495'), 'SEK'))
        self.assertEqual(self.pipeline.parse_price(u'1747,50 SEK'), (Decimal('1747.50'), 'SEK'))
