from django.test import TestCase

from theimp.parser.modules.gender import GenderMapper


class GenderMapperTest(TestCase):
    fixtures = ['initial.json']

    def setUp(self):
        self.module = GenderMapper(None)

    def test_map_gender(self):
        parsed_item = self.module({}, {}, 0)
        self.assertEqual(parsed_item, {})

        parsed_item = self.module({'gender': 'W'}, {}, 0)
        self.assertEqual(parsed_item.get('gender'), 'W')

        parsed_item = self.module({'gender': 'M'}, {}, 0)
        self.assertEqual(parsed_item.get('gender'), 'M')

        parsed_item = self.module({'gender': 'U'}, {}, 0)
        self.assertEqual(parsed_item.get('gender'), 'U')

    def test_map_gender_url(self):
        parsed_item = self.module({'url': 'http://mystore.com/products/men/my-shirt.html'}, {}, 0)
        self.assertEqual(parsed_item.get('gender'), 'M')

        parsed_item = self.module({'url': 'http://mystore.com/products/women/my-shirt.html'}, {}, 0)
        self.assertEqual(parsed_item.get('gender'), 'W')

        parsed_item = self.module({'url': 'http://mystore.com/products/unisex/my-shirt.html'}, {}, 0)
        self.assertEqual(parsed_item.get('gender'), 'U')

    def test_map_gender_name(self):
        parsed_item = self.module({'name': 'Female shirt XYZ'}, {}, 0)
        self.assertEqual(parsed_item.get('gender'), 'W')

        parsed_item = self.module({'name': 'Male pants XYZ'}, {}, 0)
        self.assertEqual(parsed_item.get('gender'), 'M')

    def test_gender_field_is_prioritized(self):
        parsed_item = self.module({'gender': 'W', 'url': 'http://mystore.com/products/men/my-shirt.html'}, {}, 0)
        self.assertEqual(parsed_item.get('gender'), 'W')

    def test_name_is_prioritizied_before_description(self):
        parsed_item = self.module({'description': 'Goes well with a male product', 'name': 'Women dress'}, {}, 0)
        self.assertEqual(parsed_item.get('gender'), 'W')

    def test_no_gender(self):
        parsed_item = self.module({'url': 'http://mystore.com/products/my-shirt.html', 'name': 'A product', 'descripton': 'short desc'}, {}, 0)
        self.assertEqual(parsed_item, {})
