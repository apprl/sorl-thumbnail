import itertools
import re

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper
from importer.framework.mapper import SkipField

REGEX_SIZE = re.compile('^[Ss]ize: .+\. ')
AVAILABILITY_MATRIX = {'n': False, 'no': False, 'not in stock': False}

class LinkshareMapper(DataMapper):
    def get_product_id(self):
        product_id = self.record.get('product-id')
        if product_id == 'HDR' or product_id == 'TRL':
            raise SkipField('remove header / footer from linkshare feeds')

        return product_id

    def get_product_name(self):
        product_name_parts = self.record.get('product-name').split(',')
        if len(product_name_parts) > 1:
            if product_name_parts[-1].strip().lower().startswith('size:'):
                del product_name_parts[-1]

        return ', '.join([x.strip() for x in product_name_parts])

    def get_variations(self):
        availability = self.get_availability()
        
        colors = ['']
        if self.record.get('color', ''):
            colors.extend(self.map_colors(self.record.get('color', '')))
        else:
            colors.extend(self.map_colors(self.record.get('product-name', '')))

        sizes = ['']
        if self.record.get('size', ''):
            sizes.extend([size.strip() for size in self.record.get('size', '').split(',')])

        variations = []
        for color, size in itertools.product(colors, sizes):
            if color or size:
                variations.append({'color': color, 'size': size, 'availability': availability})

        return variations

    def get_gender(self):
        gender = self.map_gender(self.record.get('gender', ''))
        if not gender:
            # Gender can be in category (for example in Stylebop feed)
            gender = self.map_gender(self.record.get('category', ''))

        return gender

    def get_price(self):
        discount_price = self.record.get('discount-price') or '0.00'
        return discount_price if float(discount_price) else self.record.get('retail-price')

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

        if self.record.get('secondary-category'):
            category += ' > %s' % self.record.get('secondary-category')
        if self.record.get('type'):
            category += ' > %s' % self.record.get('type')

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
        image_url = self.record.get('image-url', None)
        if image_url:
            image_url = image_url.replace('?$productdetail_main_new$', '')

        return image_url

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
