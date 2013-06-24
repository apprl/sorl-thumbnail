from theimp.parser.modules import BaseModule

from django.db.models.loading import get_model

class CategoryMapper(BaseModule):

    def __call__(self, scraped_item, parsed_item, vendor_id):
        if 'category' not in scraped_item:
            return parsed_item

        category_mapping, _ = get_model('theimp', 'CategoryMapping').objects.get_or_create(category=scraped_item['category'], vendor_id=vendor_id)
        if category_mapping.mapped_category:
            parsed_item['category'] = category_mapping.mapped_category

        return parsed_item
