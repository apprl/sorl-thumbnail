import re

from django.utils.encoding import smart_unicode
from django.db.models.loading import get_model

from theimp.parser.modules import BaseModule


class GenderMapper(BaseModule):

    def __init__(self, *args, **kwargs):
        super(GenderMapper, self).__init__(*args, **kwargs)

        self.gender_values = ['M', 'W', 'U']
        self.regexes = dict(
            (m.mapping_key, re.compile(ur'\b(?:%s)\b' % (ur'|'.join(m.get_list()),), re.I | re.UNICODE))
            for m in get_model('theimp', 'Mapping').objects.filter(mapping_type='gender')
        )

    def map_gender(self, gender_string):
        if gender_string and len(gender_string) == 1:
            gender_string_upper = gender_string.upper()
            if gender_string_upper in self.gender_values:
                return gender_string_upper

        for c, r in self.regexes.items():
            if r.search(smart_unicode(gender_string)):
                return c

        return None

    def __call__(self, scraped_item, parsed_item, vendor):
        mapped_gender = self.map_gender(scraped_item.get('gender', ''))
        if not mapped_gender:
            mapped_gender = self.map_gender(scraped_item.get('url', ''))
            if not mapped_gender:
                mapped_gender = self.map_gender(scraped_item.get('name', ''))
                if not mapped_gender:
                    mapped_gender = self.map_gender(scraped_item.get('description', ''))

        if mapped_gender:
            parsed_item['gender'] = mapped_gender
        else:
            self.delete_value(parsed_item, 'gender')

        return parsed_item
