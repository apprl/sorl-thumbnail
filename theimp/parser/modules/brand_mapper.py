from theimp.parser.modules import BaseModule

from django.db.models.loading import get_model

class BrandMapper(BaseModule):

    def __call__(self, item):
        if 'brand' not in item:
            return item

        vendor, _ = get_model('theimp', 'Vendor').objects.get_or_create(name=item['vendor'])
        brand = item['brand']
        brand_mapping, _ = get_model('theimp', 'BrandMapping').objects.get_or_create(brand=brand, vendor=vendor)
        if brand_mapping.mapped_brand:
            item['mapped_brand'] = brand_mapping.mapped_brand

        return item
