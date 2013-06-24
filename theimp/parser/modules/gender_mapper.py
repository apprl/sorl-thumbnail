import re

from django.utils.encoding import smart_unicode
from django.db.models.loading import get_model

from theimp.parser.modules import BaseModule


class GenderMapper(BaseModule):

    def __init__(self, *args, **kwargs):
        super(GenderMapper, self).__init__(*args, **kwargs)

        self.regexes = dict(
            (m.mapping_key, re.compile(ur'\b(?:%s)\b' % (ur'|'.join(m.get_list()),), re.I | re.UNICODE))
            for m in get_model('importer', 'Mapping').objects.filter(mapping_type='gender')
        )

    def map_gender(self, gender_string):
        for c, r in self.regexes.items():
            if r.search(smart_unicode(gender_string)):
                return c

        return None

    def __call__(self, scraped_item, parsed_item, vendor_id):
        if 'gender' in scraped_item:
            mapped_gender = self.map_gender(scraped_item['gender'])
            if mapped_gender:
                parsed_item['gender'] = mapped_gender

        else:
            mapped_gender = self.map_gender(scraped_item.get('url'))
            if not mapped_gender:
                mapped_gender = self.map_gender(scraped_item.get('name') + scraped_item.get('description'))

            if mapped_gender:
                parsed_item['gender'] = mapped_gender

        return parsed_item
