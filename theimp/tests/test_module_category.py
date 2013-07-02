from django.test import TestCase
from django.db.models.loading import get_model

from theimp.parser.modules.category import CategoryMapper


class CategoryMapperTest(TestCase):
    fixtures = ['initial.json']

    def setUp(self):
        self.vendor = get_model('theimp', 'Vendor').objects.create(name='TestVendor')
        get_model('theimp', 'CategoryMapping').objects.create(vendor=self.vendor, category='test-category', mapped_category='Test Category')
        get_model('theimp', 'CategoryMapping').objects.create(vendor=self.vendor, category='unmapped-category')

        self.module = CategoryMapper(None)

    def test_map_category(self):
        parsed_item = self.module({}, {}, 0)
        self.assertEqual(parsed_item, {})

        parsed_item = self.module({'category': 'test-category'}, {}, self.vendor)
        self.assertEqual(parsed_item.get('category'), 'Test Category')

    def test_map_category_invalid_vendor(self):
        parsed_item = self.module({'category': 'test-category'}, {}, None)
        self.assertEqual(parsed_item, {})

    def test_map_category_unmapped(self):
        parsed_item = self.module({'category': 'unmapped-category'}, {}, self.vendor)
        self.assertEqual(parsed_item, {})
