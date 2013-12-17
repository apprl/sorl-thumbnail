from theimp.parser.modules import BaseModule

from django.db.models.loading import get_model

class CategoryMapper(BaseModule):

    def __call__(self, item):
        if 'category' not in item:
            return item

        vendor, _ = get_model('theimp', 'Vendor').objects.get_or_create(name=item['vendor'])
        category = item['category']
        category_mapping, _ = get_model('theimp', 'CategoryMapping').objects.get_or_create(category=category, vendor=vendor)
        if category_mapping.mapped_category:
            item['mapped_category'] = category_mapping.mapped_category

        return item
