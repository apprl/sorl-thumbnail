from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper

class LinkshareMapper(DataMapper):
    genders = {'Female': 'W', 'Male': 'M'}

    def map_variations(self):
        return [{'color': c} for c in self.map_colors(self.record.get('product-name'))]

    def get_gender(self):
        return self.genders.get(self.record.get('gender'))

class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=LinkshareMapper
        self.dialect=utils.CSVPipeDelimited
        self.encoding='iso-8859-1'
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
            'price',                # Sale price, includes discount
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
            'attribute5',
            'gender',
            'attribute7',
            'agegroup',
            'attribute9',
        )
