# -*- coding: utf-8 -*-
import itertools
import re
import decimal

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper
from importer.framework.mapper import expand_entities

REGEX_SIZE = re.compile('^[Ss]ize: .+\. ')
REGEX_DECIMAL = re.compile(r'[^\d\.]')

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
        return [(self.record.get('merchant_image_url', ''), self.IMAGE_SMALL)]

    def _calculate_price(self):
        """
        Search price seems to be the lowest possible price and recommended
        retail price (RRP) seems to be the non-discounted price. It is possible
        for RRP to be zero or less than search price. If either of those
        conditions is fulfilled we can assume that no discount is active.

        Store and display price seems to use the same value as search price.
        With display price often combined with the currency field.
        """
        search_price = REGEX_DECIMAL.sub('', self.record.get('search_price', ''))
        rrp_price = REGEX_DECIMAL.sub('', self.record.get('rrp_price', ''))

        try:
            search_price_decimal = decimal.Decimal(search_price)
        except (decimal.InvalidOperation, AttributeError, ValueError, TypeError):
            return None, None

        try:
            rrp_price_decimal = decimal.Decimal(rrp_price)
        except (decimal.InvalidOperation, AttributeError, ValueError, TypeError):
            rrp_price_decimal = decimal('0.00')

        # If search price is zero or less return no discount price and no price
        # for this product
        if search_price_decimal <= decimal.Decimal('0.00'):
            return None, None

        # If search price is less than recommended retail price the product is
        # on sale (based on observed that in feeds from affiliate window)
        if search_price_decimal < rrp_price_decimal:
            return rrp_price, search_price

        # Base case.
        # If search price is non-zero and a positive value (first if statement)
        # and the recommended retail price is less than or equal to the search
        # price (second if statement) no sale is active.
        return search_price, None

    def get_discount_price(self):
        price, discount_price = self._calculate_price()

        if discount_price:
            return '%.2f' % (float(discount_price),)

        return None

    def get_price(self):
        price, discount_price = self._calculate_price()

        if price:
            return '%.2f' % (float(price),)

        return None

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
        self.unique_fields = ['product-name']
