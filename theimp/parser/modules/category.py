from theimp.parser.modules import BaseModule

from django.db.models.loading import get_model

class CategoryMapper(BaseModule):

    def __call__(self, scraped_item, parsed_item, vendor):
        if not vendor:
            return parsed_item

        if 'category' not in scraped_item:
            return parsed_item

        category_mapping, _ = get_model('theimp', 'CategoryMapping').objects.get_or_create(category=scraped_item['category'], vendor_id=vendor.pk)
        if category_mapping.mapped_category:
            parsed_item['category'] = category_mapping.mapped_category
        else:
            self.delete_value(parsed_item, 'category')

        return parsed_item
