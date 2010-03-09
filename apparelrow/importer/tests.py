import re

from django.test import TestCase

from apparelrow.importer.api import API, IncompleteDataSet


class ValidationTest(TestCase):
    
    def test_type_validation(self):
        a = API()
        
        f = lambda s,x: True if x is 'hello' else False
        
        # Positive validation
        self.assertTrue(a.validation_test(1, 'int', 0), 'Pass integer') 
        self.assertTrue(a.validation_test(1.1, 'float', 0.0), 'Pass float') 
        self.assertTrue(a.validation_test(u'hello', 'str', u''), 'Pass unicode') 
        self.assertTrue(a.validation_test('hello', 'str', ''), 'Pass string') 
        self.assertTrue(a.validation_test(False, 'bool', True), 'Pass bool') 
        self.assertTrue(a.validation_test('g. hansson 1', 'regexp', re.compile(r'^\w\. \w+ \d+$')), 'Pass regexp')
        self.assertTrue(a.validation_test('hello', 'function', f), 'Pass function') 
    
        # Negative validation
        self.assertRaises(IncompleteDataSet, a.validation_test, 'str', 'int', 0) 
        self.assertRaises(IncompleteDataSet, a.validation_test, 1, 'float', 0.0) 
        self.assertRaises(IncompleteDataSet, a.validation_test, 'hej', 'unicode', u'') 
        self.assertRaises(IncompleteDataSet, a.validation_test, 1.0, 'str', '') 
        self.assertRaises(IncompleteDataSet, a.validation_test, u'True', 'bool', True) 
        self.assertRaises(IncompleteDataSet, a.validation_test, 'HEJ. hansson 1', 'regexp', re.compile(r'^\w\. \w+ \d+$'))
        self.assertRaises(IncompleteDataSet, a.validation_test, 'bye', 'function', f) 

    
    def test_validation_recursion(self):
        a = API()
        d = {               # Key data structure
            'one': u'',
            'two': {
                'three': 0,
                'four': (0, u'',),
            },
            'five': [
                { 'six': re.compile(r'^:\d$') },
            ],
            'seven': (None, 0),
            'eight': [0],
        }
        
        t = {               # Input data
            'one': u'test value',
            'two':  {
                'three': 25,
                'four': 35,
            },
            'five': [
                { 'six': ':1' },
                { 'six': ':2' },
                { 'six': ':3' },
            ],
            'seven': 10,
            'eight': [
                1, 2, 3, 4
            ],
        }
        
        self.assertTrue(a.validate(t, keymap=d), 'Validation is recursive')    
        
        t['two']['four'] = u'hello'        
        self.assertTrue(a.validate(t, keymap=d), 'Allow a set of allowed types for same key')    
        
        # Test allowed missing key
        del t['seven']
        self.assertTrue(a.validate(t, keymap=d), 'Entries for None values may be missing')
        
        # Test failed missing key
        del t['one']
        self.assertRaises(IncompleteDataSet, a.validate, t, keymap=d)
        
        # Test unexpected key
        # FIXME: Are there an equivalent to Perl's local-statement in python? if so, use for following tests
        t['nine'] = 'whatever'
        self.assertRaises(IncompleteDataSet, a.validate, t, keymap=d)
        del t['nine']
                
        # Validation fail in array
        t['five'][1]['_new'] = 'unexpected key'
        self.assertRaises(IncompleteDataSet, a.validate, t, keymap=d)
        del t['five'][1]['_new']
        
        # Validation fail in nested dict
        t['two']['three'] = 'not a number'
        self.assertRaises(IncompleteDataSet, a.validate, t, keymap=d)
        t['two']['three'] = 10
    
    
    def test_dataset_validation(self):
        a = API()
        p = {
            'version': '0.1',
            'date': '2010-03-09T18:38:00ZCET',
            'vendor': u'Cool Clothes Store',
            'product': {
                'product-id': u'c001',
                'category': [u'Jeans'],
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
    
        self.assertTrue(a.validate(p), 'Validate product dataset')
    
    
    