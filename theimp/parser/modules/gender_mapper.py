from theimp.parser.modules import BaseModule

from django.db.models.loading import get_model

class GenderMapper(BaseModule):

    def __call__(self, scraped_item, parsed_item, vendor_id):
        if 'gender' not in scraped_item:
            # TODO: try name / description
            pass
        else:
            parsed_item['gender'] = scraped_item['gender']

        return parsed_item
