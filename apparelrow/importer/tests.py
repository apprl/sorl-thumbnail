import re, decimal

from django.test import TestCase
from apparelrow.apparel.models import Manufacturer, Category, Product, Vendor, VendorProduct
from apparelrow.importer.api import API, IncompleteDataSet, ImporterException


class ImporterAPITest(TestCase):
    
    def setUp(self):
        self.dataset = {
            'version': '0.1',
            'date': '2010-03-09T18:38:00ZCET',
            'vendor': u'Cool Clothes Store',
            'product': {
                'product-id': u'c001',
                'product-name': u'A cool pair of Jeans',
                'categories': [u'Jeans'],
                'manufacturer': u'WhateverMan',
                'price': '239.0',
                'currency': 'GBP',
                'delivery-cost': '10',
                'delivery-time': '1-2 D',
                'availability': '35',
                'image-url': 'http://www.example.com/image.jpg',
                'product-url': 'https://www.example.com/c001',
                'description': u'This is a cool par of whatever',
                'variations': [
                    {
                        'size': u'M',
                        'color': u'blue',
                        'availability': True,
                    },
                    {
                        'size': u'L',
                        'availability': True,
                    },
                    {
                        'size': u'XS',
                        'availability': '24',
                    }
                ]            
            }
        }
    
    def test_validation(self):
        a = API()
        a.dataset = self.dataset
        self.assertTrue(a.validate(), 'Validate dataset')
        
        a.dataset['version'] = 'xxx'
        self.assertRaises(ImporterException, a.validate)
    
    def test_manufacturer(self):
        a1 = API()
        
        self.assertRaises(IncompleteDataSet, lambda: a1.manufacturer)
        
        self.dataset['product']['manufacturer'] = 'The Manufacturer'
        a1.dataset = self.dataset
        
        m1 = a1.manufacturer
        self.assertTrue(isinstance(m1, Manufacturer), 'Created manufacturer')
        
        a2 = API()
        a2.dataset = self.dataset
        m2 = a2.manufacturer
        self.assertTrue(isinstance(m2, Manufacturer), 'Retrieved manufacturer')
        self.assertEqual(m1.id, m2.id, 'Got the same object back')
        
        a3 = API()
        del self.dataset['product']['manufacturer']
        a3.dataset = self.dataset
        self.assertRaises(IncompleteDataSet, lambda: a3.manufacturer)
        
    def test_vendor(self):
        a1 = API()
        
        self.assertRaises(IncompleteDataSet, lambda: a1.vendor)
        
        self.dataset['vendor'] = 'The Vendor'
        a1.dataset = self.dataset
        
        v1 = a1.vendor
        self.assertTrue(isinstance(v1, Vendor), 'Created vendor')
        
        a2 = API()
        a2.dataset = self.dataset
        v2 = a2.vendor
        self.assertTrue(isinstance(v2, Vendor), 'Retrieved vendor')
        self.assertEqual(v1.id, v2.id, 'Got the same object back')
        
        a3 = API()
        del self.dataset['vendor']
        a3.dataset = self.dataset
        self.assertRaises(IncompleteDataSet, lambda: a3.vendor)

        
    def test_categories(self):
        self.dataset['product']['categories'] = 'Single Category'
        
        a = API()
        a.dataset = self.dataset
        
        c1 = a.category
        self.assertTrue(isinstance(c1, Category), 'Created category (single)')
        self.assertEqual(c1.name, 'Single Category', 'Got correct category')
        
        a2 = API()
        a2.dataset = self.dataset
        a2.dataset['product']['categories'] = ['Single Category', 'Sub 1', 'Sub 2']
        c2 = a2.category
        self.assertTrue(isinstance(c2, Category), 'Got category')
        self.assertEqual(c2.name, 'Sub 2', 'Returned last category')
        
        c3 = c2.parent
        self.assertEqual(c3.name, 'Sub 1', 'Created parent category')
        
        c4 = c3.parent
        self.assertEqual(c4.name, 'Single Category', 'Got top level category')
        self.assertEqual(c4.id, c1.id, 'Top level category retrieved from database')
        
        a3 = API()
        a3.dataset = self.dataset
        del a3.dataset['product']['categories']
        self.assertRaises(IncompleteDataSet, lambda: a3.category)
    
    def test_import_product(self):
        a1 = API()
        a1.dataset = self.dataset
        p1 = a1.import_product()
        
        self.assertTrue(isinstance(p1, Product), 'Returned product')
        self.assertEqual(p1.manufacturer.id, a1.manufacturer.id, 'Manufacturer assigned')
        self.assertEqual(p1.sku, a1.dataset['product'].get('product-id'), 'SKU property populated')
        self.assertEqual(p1.product_name, a1.dataset['product'].get('product-name'), 'product name property populated')
        self.assertEqual(p1.description,  a1.dataset['product'].get('description'),  'Description populated')
        
        # Modify product
        a2 = API()
        a2.dataset = self.dataset
        a2.dataset['product']['product_name'] = 'A Brand New Name'
        a2.dataset['product']['description'] = 'The new description'
        p2 = a2.import_product()
        self.assertEqual(p2.id, p1.id, 'Product updated')
        self.assertNotEqual(p2.product_name, 'A Brand New Name', 'Product name NOT changed')
        self.assertEqual(p2.description, 'The new description', 'Product descrption changed')
        
        a2.dataset['product']['product-id'] = None
        a2.import_product()
        
        
    def test_import_product_vendor(self):
        a1 = API()
        a1.dataset = self.dataset
        p1 = a1.import_product()
        
        vp = VendorProduct.objects.get( product=p1, vendor=a1.vendor )
        
        self.assertTrue(isinstance(vp, VendorProduct), 'Created vendor product')
        self.assertEqual(vp.buy_url,    self.dataset['product']['product-url'], 'buy_url property')
        self.assertEqual(vp.price,      decimal.Decimal(self.dataset['product']['price']),    'price property')
        self.assertEqual(vp.currency,   self.dataset['product']['currency'], 'currency property')
        
        a2 = API()
        a2.dataset = self.dataset
        a2.dataset['product']['currency'] = 'SEK'
        p2 = a2.import_product()
        
        vp2 = VendorProduct.objects.get( product=p2, vendor=a2.vendor )
        self.assertEqual(vp2.id, vp.id, 'Same product updated')
        self.assertEqual(vp2.currency, 'SEK', 'Currency updated')
    
    def test_import_product_options(self):
        pass
        # FIXME: Check that options are added/modified
    
    def test_import_product_image(self):
        pass        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        