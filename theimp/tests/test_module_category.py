from mock import Mock

from django.test import TestCase
from django.db.models.loading import get_model

from theimp.parser.modules.category import CategoryMapper


class CategoryMapperTest(TestCase):
    fixtures = ['initial.json']

    def setUp(self):
        self.category = get_model('theimp', 'Category').objects.create(name='Category')
        self.vendor = get_model('theimp', 'Vendor').objects.create(name='TestVendor')
        get_model('theimp', 'CategoryMapping').objects.create(vendor=self.vendor, category='test-category', mapped_category=self.category)
        get_model('theimp', 'CategoryMapping').objects.create(vendor=self.vendor, category='unmapped-category')

    def test_map_category(self):
        mapper = CategoryMapper(Mock())
        parsed_item = mapper({'category': 'test-category'}, {}, self.vendor)
        self.assertEqual(parsed_item.get('category'), self.category.name)
        self.assertEqual(parsed_item.get('category_id'), self.category.pk)

    def test_map_category_no_category(self):
        mapper = CategoryMapper(Mock())
        parsed_item = mapper({}, {}, self.vendor)
        self.assertEqual(parsed_item, {})

    def test_map_category_no_vendor(self):
        mapper = CategoryMapper(Mock())
        parsed_item = mapper({'category': 'test-category'}, {}, None)
        self.assertEqual(parsed_item, {})

    def test_map_brand_no_category_and_no_vendor(self):
        mapper = CategoryMapper(Mock())
        parsed_item = mapper({}, {}, None)
        self.assertEqual(parsed_item, {})

    def test_map_category_unmapped(self):
        mapper = CategoryMapper(Mock())
        parsed_item = mapper({'category': 'unmapped-category'}, {}, self.vendor)
        self.assertEqual(parsed_item, {})
