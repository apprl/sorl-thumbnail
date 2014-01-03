from django.test import TestCase

from theimp.parser.modules.gender import GenderMapper


class GenderMapperTest(TestCase):
    fixtures = ['initial.json']

    def setUp(self):
        self.module = GenderMapper(None)

    def test_map_gender(self):
        parsed_item = self.module({}, {}, None)
        self.assertEqual(parsed_item, {})

        parsed_item = self.module({'gender': 'W'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'W')

        parsed_item = self.module({'gender': 'M'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'M')

        parsed_item = self.module({'gender': 'U'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'U')

    def test_map_gender_url(self):
        parsed_item = self.module({'url': 'http://mystore.com/products/men/my-shirt.html'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'M')

        parsed_item = self.module({'url': 'http://mystore.com/products/women/my-shirt.html'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'W')

        parsed_item = self.module({'url': 'http://mystore.com/products/unisex/my-shirt.html'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'U')

    def test_map_gender_url_2(self):
        parsed_item = self.module({'url': 'http://shop.acnestudios.com/shop/men/bags/nico-black.html'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'M')

    def test_map_gender_name(self):
        parsed_item = self.module({'name': 'Female shirt XYZ'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'W')

        parsed_item = self.module({'name': 'Male pants XYZ'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'M')

    def test_gender_field_is_prioritized(self):
        parsed_item = self.module({'gender': 'W', 'url': 'http://mystore.com/products/men/my-shirt.html'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'W')

    def test_name_is_prioritizied_before_description(self):
        parsed_item = self.module({'description': 'Goes well with a male product', 'name': 'Women dress'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'W')

    def test_no_gender(self):
        parsed_item = self.module({'url': 'http://mystore.com/products/my-shirt.html', 'name': 'A product', 'descripton': 'short desc'}, {}, None)
        self.assertEqual(parsed_item, {})

    def test_fallback_if_invalid_gender(self):
        parsed_item = self.module({'gender': 'Invalid...', 'url': 'http://mystore.com/products/men/my-shirt.html'}, {}, None)
        self.assertEqual(parsed_item.get('gender'), 'M')
