import logging, re

from django.db import transaction

from apparel.models import *

"""
Provides an API for importing and setting up product data for the ApparelRow
web application

Synopsis

    api = API()
    api.import(data)

Required Data Structure

{
    'version': '0.1',
    'date': '2010-02-11 15:41:01 UTC',
    'vendor': 'Cali Roots',
    'product': {
        'product-id': '375512-162',
        'product-name': 'Flight 45',
        'category': 'Sneakers',
        'manufacturer': 'Jordan',
        'price': 1399.00,
        'currency': 'SEK',
        'delivery-cost': 99.00
        'delivery-time': '3-5 D',
        'availability': True OR a number (0 for not available),
        'product-url': 'http://caliroots.com/system/search/product_vert.asp?id=20724',
        'image-url': 'http://caliroots.com/data/product/images/20724200911114162028734214_L.jpg',
        'description': 'Classic Flight 45',
        'variations':
        [
            {
                'size': '10',
                'color': 'red',
                'availability': true OR a number
            },
            ...
        ]
    }
}

 
"""

class API():
    _regexp = re.compile(r'')  # FIXME: Anyone know how to identify a regular expression object in python apart from doing "type(re.compile(something))"
    key_structure = {
        'version': lambda s, x: True if x == s.version else False,
        # FIXME: There are libraries that supports ISO8601 parsing, but I think
        # we should require the timezone bit
        'date': re.compile(r'^\d{4}-\d{2}-\d{2}(?:T| )\d{2}:\d{2}:\d{2}(?:Z| )(?:\w{3,4}|(?:\+|-)?\d{2}:?\d{2})$'),
        'vendor': u'',
        'product': {
            'product-id': u'',
            'category': [
                u'',
            ],
            'manufacturer': u'',
            'price': (0, 0.0,),
            'currency': re.compile(r'^[A-Z]{3}$'),
            'delivery-cost': (0, 0.0,),
            'delivery-time': re.compile(r'^\d+(?:-\d+)? D$'),
            'availability': (True, 0,),
            'image-url': re.compile(r'^https?://'),
            'product-url': re.compile(r'^https?://'),
            'description': u'',
            'variations': [
                {
                    'size': (None, 0, u'',),
                    'color': (None, u'',),   # FIXME: Check against list of supported colors
                    'availability': (True, 0,),
                }
            ]
            
        }
    }
    
    def __init__(self):
        self.version      = "0.1"        
        self.product      = None
        self.categories   = []
        self.manufacturer = None
    
    @transaction.commit_on_success
    def import_dataset(self, data):
        """
        Imports the Product and related data specified in the data structure. 
        """
        
        try:
            self.validate(data)
            self.do_import(data)
        except ImporterException, e:
            # Log ImporterException
            logging.error('%s, record skipped', e)
            raise
        else:
            logging.info('Imported %s', self.product)
    
    def validate(self, data, keymap=key_structure):
        """
        Validates a data structure. Returns True on success, will otherwise throw
        an exception
        """
        
        if not isinstance(data, dict):
            raise IncompleteDataSet('Expecting a dict, got "%s"' % data)
        
        for (k, v) in data.iteritems():
            
            if k not in keymap: raise IncompleteDataSet('Unknown key %s' % k)
            
            test = keymap[k]
            
            # Handle recursiveness
            if isinstance(test, dict):
                self.validate(v, test)
            
            elif isinstance(test, list):
                if isinstance(test[0], dict):
                    # Descend into dictionary
                    for i in v: self.validate(i, test[0]) 
                else:
                    # Check all values in array
                    for i in v: self.validation_test(i, k, test[0])
            
            elif isinstance(test, tuple):
                # Run several tests, only one has to pass
                for t in test:
                    try:
                        # run test
                        self.validation_test(v, k, t)
                    except IncompleteDataSet:
                        pass
                    except Exception:
                        raise
                    else:
                        # if it passed, stop checking and move on to next item
                        break
                else:
                    # If all items were processed, re-throw last caught exception
                    raise
            else:
                # Run test
                self.validation_test(v, k, test)
        
        
        # Dataset is valid, now check that no required keys are missing
        for (k, v) in keymap.iteritems():
            l = (v,) if not isinstance(v, tuple) else v
            if None in l: continue  # If None types are allowed to be missed out
            if not k in data: raise IncompleteDataSet('Missing required key %s' % k)
        
        return True
        
    def validation_test(self, value, prop, test):
        if test is None and value is None:
            return True
        
        elif callable(test):
            if test(self, value): return True 

        elif isinstance(test, type(self._regexp)):
            if test.match(value): return True

        elif isinstance(value, type(test)):
            # FIXME: Is this test really safe?           
            return True 
                
        raise IncompleteDataSet('Value "%s" not valid for property "%s"' % (value, prop))


class ImporterException(Exception):
    """
    An exception base class that will prevent the current data to be imported
    and any change to be rolled back.
    """
    pass

class SkipProduct(ImporterException):
    """
    For some reason the product should be skipped.
    """
    pass

class IncompleteDataSet(ImporterException):
    """
    The product could not be imported because required data is missing or 
    malformatted.
    """
    pass

