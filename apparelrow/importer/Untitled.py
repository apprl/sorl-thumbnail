data_structure = {
    'version': lambda s, x: True if x == s.version,
    'date': datetime,
    'vendor': u'',
    'product': {
        'product-id': u'',
        'category': u'',
        'manufacturer': u'',
        'price': 0.0,
        'currency': r'^[A-Z]{3}$',
        'delivery-cost': 0.0,
        'delivery-time': r'^\d+(?:-\d+)? D$',
        'availability': (True, 0,),
        'image-url': r'^https?://',
        'product-url': r'^https?://',
        'description': u'',
        'variations': [
            {
                'size': (None, 0,),
                'color': (None, u'',),   # FIXME: Check against list of supported colors
                'availability': (True, 0,),
            }
        ]
        
    }
)