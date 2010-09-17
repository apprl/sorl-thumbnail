import re
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
    def set_product_name(self):
        return self.record.get('name')
    
    def set_currency(self):
        raise SkipField('I do not care about this field')
    

class DummyProvider(Provider):
    pass

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
        self.assertEqual(f['vendor'], self.mapper.provider.name, 'Vendor name')

        p = f['product']
        self.assertFalse('currency' in p, 'SkipField is causing field to be ignored')
        self.assertEqual(p['price'], None, 'Missing field is filled with None value')
        self.assertEqual(p['variances'], [], 'variances defaults to empty array')
        
    

if __name__ == '__main__':
    unittest.main()

