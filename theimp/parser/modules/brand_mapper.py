from theimp.parser.modules import BaseModule

from django.db.models.loading import get_model

class BrandMapper(BaseModule):

    def __call__(self, scraped_item, parsed_item, vendor_id):
        if 'brand' not in scraped_item:
            return parsed_item

        brand_mapping, _ = get_model('theimp', 'BrandMapping').objects.get_or_create(brand=scraped_item['brand'], vendor_id=vendor_id)
        if brand_mapping.mapped_brand:
            parsed_item['brand'] = brand_mapping.mapped_brand
        else:
            self.delete_value(parsed_item, 'brand')

        return parsed_item
