from django.test import TestCase, TransactionTestCase

from importer.framework.mapper import DataMapper, SkipField
from importer.framework.provider import Provider

#    'version': '0.1',
#    'date': '2010-02-11 15:41:01 UTC',
#    'vendor': 'Cali Roots',
#    'product': {
#        'product-id': '375512-162',
#        'product-name': 'Flight 45',
#        'categories': 'Sneakers',
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

class DataMapperTest(TestCase):
    def setUp(self):
        self.mapper = DummyDataMapper(DummyProvider(), record={
            'product_id': 'the id',
            'name': 'the name',
            'product_url': 'the url',
            
            'unitcost': 1023
        })
    
    
    def test_map_field_record(self):
        self.assertEqual(self.mapper.map_field('product_url'), 'the url')
    
    def test_map_field_method(self):
        self.assertEqual(self.mapper.map_field('product-name'), 'the name')
    
    def test_map_field_nonexistent(self):
        self.assertEqual(self.mapper.map_field('some-field'), None)
    
    def test_map_field_skip(self):
        self.assertRaises(SkipField, self.mapper.map_field, 'currency')
    

if __name__ == '__main__':
    unittest.main()

