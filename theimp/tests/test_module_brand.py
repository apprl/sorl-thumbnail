from django.test import TestCase
from django.db.models.loading import get_model

from theimp.parser.modules.brand import BrandMapper


class BrandMapperTest(TestCase):
    fixtures = ['initial.json']

    def setUp(self):
        self.brand = get_model('apparel', 'Brand').objects.create(name='Brand')
        self.vendor = get_model('theimp', 'Vendor').objects.create(name='TestVendor')
        get_model('theimp', 'BrandMapping').objects.create(vendor=self.vendor, brand='test-brand', mapped_brand=self.brand)
        get_model('theimp', 'BrandMapping').objects.create(vendor=self.vendor, brand='unmapped-brand')

        self.module = BrandMapper(None)

    def test_map_brand(self):
        parsed_item = self.module({}, {}, 0)
        self.assertEqual(parsed_item, {})

        parsed_item = self.module({'brand': 'test-brand'}, {}, self.vendor)
        self.assertEqual(parsed_item.get('brand'), 'Brand')
        self.assertEqual(parsed_item.get('brand_id'), 1)

    def test_map_brand_invalid_vendor(self):
        parsed_item = self.module({'brand': 'test-brand'}, {}, None)
        self.assertEqual(parsed_item, {})

    def test_map_brand_unmapped(self):
        parsed_item = self.module({'brand': 'unmapped-brand'}, {}, self.vendor)
        self.assertEqual(parsed_item, {})
