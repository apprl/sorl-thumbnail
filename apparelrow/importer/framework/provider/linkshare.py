import itertools

from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper

class LinkshareMapper(DataMapper):
    genders = {'Female': 'W', 'Male': 'M'}

    def get_variations(self):
        availability = self.get_availability()
        
        colors = []
        if self.record.get('color', ''):
            colors = self.map_colors(self.record.get('color', ''))

        sizes = []
        if self.record.get('size', ''):
            sizes = [size.strip() for size in self.record.get('size', '').split(',')]

        variations = []
        for color, size in itertools.product(colors, sizes):
            variations.append({'color': color, 'size': size, 'availability': availability})
        
        return variations

        #if self.record.get('color'):
            #return [{'color': c} for c in self.map_colors(self.record.get('color'))]

        #return [{'color': c} for c in self.map_colors(self.record.get('product-name'))]

    def get_gender(self):
        return self.genders.get(self.record.get('gender'))

    def get_price(self):
        return self.record.get('discount-price') or self.record.get('retail-price')

    def get_category(self):
        category = self.record.get('category')
        if self.record.get('secondary-category'):
            category = category + ' > ' + self.record.get('secondary-category')

        return category

    def get_availability(self):
        #return True if self.record.get('availability') else False
        if self.record.get('availability').lower().strip() == 'in stock':
            return True

        return False


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
            'attribute4',
            'color',
            'gender',
            'attribute7',
            'agegroup',
            'attribute9',
        )
