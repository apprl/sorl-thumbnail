from mock import Mock

from django.test import TestCase
from django.db.models.loading import get_model
from django.test.utils import override_settings

from theimp.parser.modules.brand import BrandMapper


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class BrandMapperTest(TestCase):
    fixtures = ['initial.json']

    def setUp(self):
        self.brand = get_model('apparel', 'Brand').objects.create(name='Brand')
        self.vendor = get_model('theimp', 'Vendor').objects.create(name='TestVendor')
        get_model('theimp', 'BrandMapping').objects.create(vendor=self.vendor, brand='test-brand', mapped_brand=self.brand)
        get_model('theimp', 'BrandMapping').objects.create(vendor=self.vendor, brand='unmapped-brand')

    def test_map_brand(self):
        mapper = BrandMapper(Mock())
        parsed_item = mapper({'brand': 'test-brand'}, {}, self.vendor)
        self.assertEqual(parsed_item.get('brand'), self.brand.name)
        self.assertEqual(parsed_item.get('brand_id'), self.brand.pk)

    def test_map_none_brand(self):
        mapper = BrandMapper(Mock())
        parsed_item = mapper({'brand': None}, {}, self.vendor)
        self.assertEqual(parsed_item, {})

    def test_map_empty_brand(self):
        mapper = BrandMapper(Mock())
        parsed_item = mapper({'brand': ''}, {}, self.vendor)
        self.assertEqual(parsed_item, {})

    def test_map_brand_no_brand(self):
        mapper = BrandMapper(Mock())
        parsed_item = mapper({}, {}, self.vendor)
        self.assertEqual(parsed_item, {})

    def test_map_brand_no_vendor(self):
        mapper = BrandMapper(Mock())
        parsed_item = mapper({'brand': 'test-brand'}, {}, None)
        self.assertEqual(parsed_item, {})

    def test_map_brand_no_brand_and_no_vendor(self):
        mapper = BrandMapper(Mock())
        parsed_item = mapper({}, {}, None)
        self.assertEqual(parsed_item, {})

    def test_map_brand_unmapped(self):
        mapper = BrandMapper(Mock())
        parsed_item = mapper({'brand': 'unmapped-brand'}, {}, self.vendor)
        self.assertEqual(parsed_item, {})
