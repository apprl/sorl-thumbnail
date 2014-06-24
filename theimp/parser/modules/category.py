from theimp.parser.modules import BaseModule

from django.db.models.loading import get_model
import logging

log = logging.getLogger( __name__ )

class CategoryMapper(BaseModule):

    def __call__(self, scraped_item, parsed_item, vendor, product=None):
        if not vendor:
            return parsed_item

        if 'category' not in scraped_item or not scraped_item['category']:
            return parsed_item

        category_mapping, _ = get_model('theimp', 'CategoryMapping').objects.get_or_create(category=scraped_item['category'], vendor_id=vendor.pk)
        if category_mapping.mapped_category:
            parsed_item['category'] = category_mapping.mapped_category.name
            parsed_item['category_id'] = category_mapping.mapped_category.pk
        else:
            log.warn('Category mapping failed, category = %s Vendor = %s'
                % (scraped_item['category'],vendor))
            self.delete_value(parsed_item, 'category')
            self.delete_value(parsed_item, 'category_id')

        if product:
            product.category_mapping = category_mapping

        return parsed_item
