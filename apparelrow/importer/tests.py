import re

from django.test import TestCase
from apparelrow.apparel.models import Manufacturer, Category, Product, Vendor
from apparelrow.importer.api import API, IncompleteDataSet, ImporterException


class ValidationTest(TestCase):
    
    def setUp(self):
        self.dataset = {
            'version': '0.1',
            'date': '2010-03-09T18:38:00ZCET',
            'vendor': u'Cool Clothes Store',
            'product': {
                'product-id': u'c001',
                'categories': [u'Jeans'],
                'manufacturer': u'WhateverMan',
                'price': 239.0,
                'currency': 'GBP',
                'delivery-cost': 10,
                'delivery-time': '1-2 D',
                'availability': 35,
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
                        'availability': 24,
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
    