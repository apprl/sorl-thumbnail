import itertools
import re

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper
from importer.api import SkipProduct

REGEX_SIZE = re.compile('^[Ss]ize: .+\. ')
AVAILABILITY_MATRIX = {'n': False, 'no': False, 'not in stock': False, 'out of stock': False, 'no stock': False}

class LinkshareMapper(DataMapper):
    def get_product_id(self):
        product_id = self.record.get('product-id')
        if product_id == 'HDR' or product_id == 'TRL':
            raise SkipProduct('remove header / footer from linkshare feeds')

        # remove kids products
        agegroup = self.record.get('agegroup')
        if agegroup:
            agegroup = agegroup.lower()
            if agegroup == 'kids' or agegroup == 'kid' or agegroup == 'children' or agegroup == 'child':
                raise SkipProduct('kids product')

        return product_id

    def get_product_name(self):
        product_name_parts = self.record.get('product-name').split(',')
        if len(product_name_parts) > 1:
            if product_name_parts[-1].strip().lower().startswith('size:'):
                del product_name_parts[-1]

        return ', '.join([x.strip() for x in product_name_parts])

    def get_variations(self):
        availability = self.get_availability()

        colors = self.get_color()
        sizes = self.get_size()

        variations = []
        for color, size in itertools.product(colors, sizes):
            if color or size:
                variations.append({'color': color, 'size': size, 'availability': availability})

        return variations

    def get_size(self):
        sizes = ['']
        if self.record.get('size', ''):
            sizes.extend([size.strip() for size in self.record.get('size', '').split(',')])
        return sizes

    def get_color(self):
        colors = []
        if self.record.get('color', ''):
            colors.extend(self.map_colors(self.record.get('color', '')))
        else:
            colors.extend(self.map_colors(self.record.get('product-name', '')))
        return colors

    def get_gender(self):
        gender = self.map_gender(self.record.get('gender', ''))
        if not gender:
            gender = self.map_gender(self.record.get('category', ''))

        return gender

    def get_discount_price(self):
        return self.record.get('discount-price') or None

    def get_price(self):
        return self.record.get('retail-price') or None

    def get_manufacturer(self):
        manufacturer = self.record.get('manufacturer') or self.record.get('brand')
        manufacturer_parts = [m.strip() for m in manufacturer.split(',')]
        if len(manufacturer_parts) > 1:
            if len(manufacturer_parts[0]) <= 5:
                del manufacturer_parts[0]

            return ', '.join(manufacturer_parts)

        return manufacturer

    def get_description(self):
        description = self.record.get('long-description') or self.record.get('description')
        description = REGEX_SIZE.sub('', description, re.IGNORECASE)

        if self.record.get('material'):
            description += " (%s)" % self.record.get('material')

        return description

    def get_category(self):
        category = self.record.get('category')

        gender = self.get_gender()
        if gender:
            category = '%s > %s' % (gender, category)

        if self.record.get('secondary-category'):
            category += ' > %s' % self.record.get('secondary-category')

        return category

    def get_availability(self):
        availability = self.record.get('availability')
        if availability:
            if AVAILABILITY_MATRIX.get(availability.strip().lower(), True):
                try:
                    availability = int(availability)
                except ValueError:
                    availability = -1
                return availability
            else:
                return 0

        return None

    def get_image_url(self):
        return [(self.record.get('image-url', ''), self.IMAGE_SMALL)]

class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=LinkshareMapper
        self.dialect=utils.CSVPipeDelimited
        self.fieldnames=(
            'product-id',
            'product-name',
            'sku',
            'category',
            'secondary-category',
            'product-url',
            'image-url',
            'buy-url',
            'description',
            'long-description',
            'discount',
            'discount-type',
            'discount-price',       # Sale price, includes discount
            'retail-price',
            'available-from',
            'available-to',
            'brand',
            'delivery-price',
            'keywords',             # ~~ delimited
            'manufacturer-part-no',
            'manufacturer',
            'shipping-information',
            'availability',
            'universal-product-code',
            'classification-id',
            'currency',
            'm1',                   # blank field
            'tracking-pixel-url',
            'miscellaneous-attribute',
            'attribute2',
            'size',                 # attribute 3
            'material',             # attribute 4
            'color',
            'gender',
            'type',                 # attribute 7
            'agegroup',
            'attribute9',
        )
        self.unique_fields = ['product-name']
