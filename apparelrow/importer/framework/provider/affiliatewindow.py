# -*- coding: utf-8 -*-
import itertools
import re

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper
from importer.framework.mapper import expand_entities

REGEX_SIZE = re.compile('^[Ss]ize: .+\. ')
REGEX_DECIMAL = re.compile(r'[^\d.]+')

class AffiliateWindowMapper(DataMapper):
    
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

        return expand_entities(product_name)

    def get_product_url(self):
        return self.record['aw_deep_link']

    def get_image_url(self):
        return self.record['aw_image_url']

    def get_price(self):
        try:
            display_price = float(REGEX_DECIMAL.sub('', self.record.get('display_price', '')))
        except ValueError:
            display_price = 0

        try:
            store_price = float(REGEX_DECIMAL.sub('', self.record.get('store_price', '')))
        except ValueError:
            store_price = 0

        if display_price == 0 and store_price == 0:
            return None
        elif display_price == 0 and store_price > 0:
            return '%.2f' % (store_price,)
        elif display_price > 0 and store_price == 0:
            return '%.2f' % (display_price,)
        else:
            return '%.2f' % (min(store_price, display_price),)

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
            try:
                stock_quantity = int(self.record.get('stock_quantity', '-'))
            except ValueError:
                return -1

            return stock_quantity if stock_quantity > 0 else -1

        return None

    def get_variations(self):
        availability = self.get_availability()
        specification = self.record.get('specification', '')
        
        colors = ['']
        colors.extend(self.map_colors(self.get_product_name() + specification))

        sizes = ['']
        if specification:
            result = re.match(r'Sizes: (.+)\|Colours', specification)
            if result:
                sizes.extend(result.group(1).split('|'))
            else:
                sizes.extend([specification])

        variations = []
        for color, size in itertools.product(colors, sizes):
            if color or size:
                variations.append({'color': color, 'size': size, 'availability': availability})

        return variations

class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=AffiliateWindowMapper
        self.dialect=utils.CSVPipeDelimitedQuoted

    def should_merge(self, new_record):
        return self.record['product']['product-name'] == new_record['product']['product-name']

    def merge(self, new_record):
        pass
