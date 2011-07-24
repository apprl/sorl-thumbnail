# -*- coding: utf-8 -*-
import itertools
import re

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper

REGEX_SIZE = re.compile('^[Ss]ize: .+\. ')

class LibertyMapper(DataMapper):
    
    def get_product_id(self):
        return self.record['merchant_product_id']

    def get_product_name(self):
        # Remove size from end of name
        product_name_parts = self.record.get('product_name').split(',')
        if len(product_name_parts) > 1:
            if product_name_parts[-1].strip().lower().startswith('size:'):
                del product_name_parts[-1]

        product_name = ', '.join([x.strip() for x in product_name_parts])

        # Remove manufacturer from end of name
        manufacturer = self.get_manufacturer()
        product_name = re.sub(r', %s$' % (manufacturer,), '', product_name, re.IGNORECASE)

        return product_name

    def get_product_url(self):
        return self.record['aw_deep_link']

    def get_image_url(self):
        return self.record['aw_image_url']

    def get_price(self):
        return self.record.get('display_price')

    def get_category(self):
        return '%s >> %s' % (self.record.get('category_name'), self.record.get('merchant_category'))

    def get_gender(self):
        return self.map_gender(self.get_category())

    def get_manufacturer(self):
        if self.record.get('brand_name'):
            return self.record.get('brand_name')

        return self.record.get('merchant_name')

    def get_description(self):
        return REGEX_SIZE.sub('', self.record.get('description', ''), re.IGNORECASE)

    def get_availability(self):
        if self.record.get('in_stock'):
            return -1

        return None

    def get_variations(self):
        availability = self.get_availability()
        
        colors = ['']
        colors.extend(self.map_colors(self.get_product_name() + self.record.get('specification', '')))

        sizes = ['']
        if self.record.get('specification', False):
            sizes.extend([self.record.get('specification')])

        variations = []
        for color, size in itertools.product(colors, sizes):
            if color or size:
                variations.append({'color': color, 'size': size, 'availability': availability})

        return variations

class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=LibertyMapper
        self.dialect=utils.CSVPipeDelimitedQuoted

    def should_merge(self, new_record):
        return self.record['product']['product-name'] == new_record['product']['product-name']

    def merge(self, new_mapped_record):
        pass
