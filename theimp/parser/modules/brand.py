from theimp.parser.modules import BaseModule

from django.db.models.loading import get_model

import logging

log = logging.getLogger( __name__ )

class BrandMapper(BaseModule):

    def __call__(self, scraped_item, parsed_item, vendor, product=None):
        if not vendor:
            return parsed_item

        if 'brand' not in scraped_item or not scraped_item['brand']:
            log.warn('Brand key is not found in scraped item or it is None.')
            return parsed_item

        brand_mapping, _ = get_model('theimp', 'BrandMapping').objects.get_or_create(brand=scraped_item['brand'], vendor_id=vendor.pk)
        if brand_mapping.mapped_brand:
            parsed_item['brand'] = brand_mapping.mapped_brand.name
            parsed_item['brand_id'] = brand_mapping.mapped_brand.pk
        else:
            log.warn('Brandmapping failed. Filter brand = %s and vendor = %s'
                     % (scraped_item['brand'],vendor))
            self.delete_value(parsed_item, 'brand')
            self.delete_value(parsed_item, 'brand_id')

        if product:
            product.brand_mapping = brand_mapping

        return parsed_item
