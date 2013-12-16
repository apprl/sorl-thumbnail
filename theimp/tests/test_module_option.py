from django.test import TestCase

from theimp.parser.modules.option import OptionMapper


class GenderMapperTest(TestCase):
    fixtures = ['initial.json']

    def setUp(self):
        self.module = OptionMapper(None)

    def test_map_nothing(self):
        parsed_item = self.module({}, {}, None)
        self.assertEqual(parsed_item, {})

    def test_map_colors(self):
        parsed_item = self.module({'colors': 'red'}, {}, None)
        self.assertEqual(parsed_item.get('colors'), ['red'])
        self.assertEqual(parsed_item.get('patterns'), None)

        parsed_item = self.module({'colors': 'green'}, {}, None)
        self.assertEqual(parsed_item.get('colors'), ['green'])
        self.assertEqual(parsed_item.get('patterns'), None)

        parsed_item = self.module({'colors': 'what a lovely red and blue shirt'}, {}, None)
        self.assertEqual(sorted(parsed_item.get('colors')), sorted(['red', 'blue']))
        self.assertEqual(parsed_item.get('patterns'), None)

    def test_map_patterns(self):
        parsed_item = self.module({'colors': 'striped'}, {}, None)
        self.assertEqual(parsed_item.get('patterns'), ['striped'])
        self.assertEqual(parsed_item.get('colors'), None)

        parsed_item = self.module({'colors': 'dotted'}, {}, None)
        self.assertEqual(parsed_item.get('patterns'), ['dotted'])
        self.assertEqual(parsed_item.get('colors'), None)

        parsed_item = self.module({'colors': 'lovely striped and checked red shirt'}, {}, None)
        self.assertEqual(sorted(parsed_item.get('patterns')), sorted(['striped', 'checkers']))
        self.assertEqual(parsed_item.get('colors'), ['red'])

    def test_map_option_with_invalid_option_type(self):
        result = self.module.map_option('invalid_type', 'string with red color')
        self.assertIsNone(result)
