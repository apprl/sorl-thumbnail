# -*- coding: utf-8 -*-

import re
from mock import Mock

from django.test import TestCase, TransactionTestCase

from importer.framework.mapper import DataMapper, SkipField
from importer.framework.provider import Provider
from importer.models import VendorFeed
from apparel import models as apparel



#    'version': '0.2',
#    'date': '2010-02-11 15:41:01 UTC',
#    'vendor': 'Cali Roots',
#    'product': {
#        'product-id': '375512-162',
#        'product-name': 'Flight 45',
#        'categories': 'Sneakers',
#        'category': 'Sneakers',
#        'manufacturer': 'Jordan',
#        'price': 1399.00,
#        'currency': 'SEK',
#        'delivery-cost': 99.00,
#        'delivery-time': '3-5 D',
#        'availability': True OR a number (0 for not available),
#        'product-url': 'http://caliroots.com/system/search/product_vert.asp?id=20724',
#        'image-url': 'http://caliroots.com/data/product/images/20724200911114162028734214_L.jpg',
#        'description': 'Classic Flight 45',
#        'variations':
#        [
#            {
#                'size': '10',
#                'color': 'red',
#                'availability': true OR a number
#            },
#            ...
#        ]
#    }


class DummyDataMapper(DataMapper):
    def get_product_name(self):
        return self.record.get('name')
    
    def get_currency(self):
        raise SkipField('I do not care about this field')
    

class DummyProvider(Provider):
    pass
    
class MapperProcessTest(TestCase):
    def setUp(self):
        feed = Mock(spec=VendorFeed)
        feed.vendor = Mock(spec=apparel.Vendor)
        feed.vendor.name = 'whatever'
        
        self.mapper = DataMapper(Mock(spec=DummyProvider(feed)))
        self.mapper.preprocess     = Mock()
        self.mapper.postprocess    = Mock()
        self.mapper.map_field      = Mock()
        
    def test_translate(self):
        self.mapper.translate()
        self.assertTrue(self.mapper.preprocess.called, 'Called preprocess()')
        self.assertTrue(self.mapper.postprocess.called, 'Called postprocess()')
        self.assertEquals(
            self.mapper.map_field.call_args_list, 
            [
                (('date',), {}),
                (('product-id',), {}), 
                (('product-name',), {}), 
                (('category',), {}), 
                (('manufacturer',), {}), 
                (('price',), {}), 
                (('currency',), {}), 
                (('delivery-cost',), {}), 
                (('delivery-time',), {}), 
                (('image-url',), {}), 
                (('product-url',), {}), 
                (('description',), {}), 
                (('availability',), {}),
                (('variations',), {}),
            ],
            'Called map_field() with each field'
        )


class FieldMapperTest(TestCase):
    def setUp(self):
        self.feed = VendorFeed.objects.create(
            vendor=apparel.Vendor.objects.create(name='My Vendor'),
            url='http://example.com/feed.csv',
            username='the username',
            password='the password',
            provider_class='DummyProvider',
        )
        self.mapper = DummyDataMapper(DummyProvider(self.feed), record={
            'product_id': 'the id',
            'name': 'the name',
            'product-url': 'the url',
            'price': ' the    price   ',
            'description': """
                Some <b>funky</b> description<br/> containing 
                HTML and n&aring;gra entities
            """
        })        
    
    def test_map_field_record(self):
        self.assertEqual(self.mapper.map_field('product-url'), 'the url', 'Mapped field to data dict')
        self.assertEqual(self.mapper.map_field('product_url'), None, 'The - to / conversion does not apply to fields')
    
    def test_map_field_method(self):
        self.assertEqual(self.mapper.map_field('product-name'), 'the name')
    
    def test_map_field_nonexistent(self):
        self.assertEqual(self.mapper.map_field('some-field'), None)
    
    def test_map_field_skip(self):
        self.assertRaises(SkipField, self.mapper.map_field, 'currency')
    
    def test_map_fields(self):
        f = self.mapper.translate()
        self.assertTrue(isinstance(f, dict))
        self.assertTrue('product' in f)
        self.assertTrue('version' in f)
        self.assertTrue(re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z(?:.+?)?', f.get('date')))
        self.assertEqual(f['vendor'], 'My Vendor', 'Vendor name')
        
        p = f['product']
        
        self.assertFalse('currency' in p, 'SkipField is causing field to be ignored')
        self.assertEqual(p['delivery-time'], None, 'Missing field is filled with None value')
        self.assertEqual(p['variations'], [], 'variances defaults to empty array')
    
    def test_postprocess(self):
        f = self.mapper.translate()
        self.assertEqual(
            f['product']['description'],
            u'Some funky description containing \n HTML and n\xe5gra entities',
            'HTML stripped from description'
        )
        self.assertEqual(
            f['product']['price'],
            u'the price',
            'Whitespaces stripped from all fields'
        )

class HelperMethodsTest(TestCase):
    def setUp(self):
        self.feed = VendorFeed.objects.create(
            vendor=apparel.Vendor.objects.create(name='My Vendor'),
            url='http://example.com/feed.csv',
            username='the username',
            password='the password',
            provider_class='DummyProvider',
        )
        self.mapper = DummyDataMapper(DummyProvider(self.feed), record={
            'product_id': 'the id',
            'name': 'the name',
            'product-url': 'the url',
        })        
    
    def test_map_colors(self):
        c = self.mapper.map_colors(u'Here is a string with Black, navy and red')
        self.assertEqual(set(c), set((u'black', u'blue', u'red',)), 'Mapped colors')
    
    def test_trim(self):
        self.assertEqual(self.mapper.trim('   xxx xx xxx   '), 'xxx xx xxx', 'Trimmed leading and tailing whitespaces')
        self.assertEqual(self.mapper.trim('xxx xx xxx   '), 'xxx xx xxx', 'Trimmed tailing whitespaces')
        self.assertEqual(self.mapper.trim('   xxx xx xxx'), 'xxx xx xxx', 'Trimmed leading whitespaces')
    
    def test_trim_type(self):
        """
        Pass in anything to trim without it failing
        """
        
        self.assertEqual(self.mapper.trim(None),  None,  'Call trim() with None')
        self.assertEqual(self.mapper.trim(False), False, 'Call trim() with Boolean')
        self.assertEqual(self.mapper.trim(121),   121,   'Call trim() with intiger')
        self.assertEqual(self.mapper.trim(11.12), 11.12, 'Call trim() with float')
        
        self.assertEqual(self.mapper.trim(['  je h ', 'a   a a']), ['je h', 'a a a'], 'Call trim() with list of strings')
        self.assertEqual(self.mapper.trim([' ja a ', [' b ah']]), [' ja a ', [' b ah']], 'Call trim() with list of mixed data types')
        self.assertEqual(self.mapper.trim('  c c'), 'c c', 'Call trim() with string')
        self.assertEqual(self.mapper.trim({'a': 'A', 'b ': 'B '}), {'a': 'A', 'b ': 'B '}, 'Call trim() with dict')
    
    def test_strip_html(self):
        
        self.assertEqual(self.mapper.strip_html(u"""
            blah\n<p attr="value"
        >n&aring;got roligt
        </p>
        <b>&#160;hej&#x0046;</b>
        hej<br>d&aring;
        
        
            """),
            u'blah\n n\xe5got roligt\n \n \xa0hejF \n hej d\xe5',
            'Removed HTML and expanded entities'
        )


if __name__ == '__main__':
    unittest.main()

