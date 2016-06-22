import re

from django.db.models.loading import get_model
from django.utils.encoding import smart_unicode

from theimp.parser.modules import BaseModule
import logging

log = logging.getLogger( __name__ )

class OptionMapper(BaseModule):

    def __init__(self, *args, **kwargs):
        super(OptionMapper, self).__init__(*args, **kwargs)

        self.regexes = {}
        self.regexes['color'] = dict(
            (m.mapping_key, re.compile(ur'\b(?:%s)\b' % (ur'|'.join(m.get_list()),), re.I | re.UNICODE))
            for m in get_model('theimp', 'Mapping').objects.filter(mapping_type='color')
        )
        self.regexes['pattern'] = dict(
            (m.mapping_key, re.compile(ur'\b(?:%s)\b' % (ur'|'.join(m.get_list()),), re.I | re.UNICODE))
            for m in get_model('theimp', 'Mapping').objects.filter(mapping_type='pattern')
        )

    def map_option(self, option_type, value):
        if option_type in self.regexes:
            return [c for c, r in self.regexes[option_type].items() if r.search(smart_unicode(value))]

        return None

    def __call__(self, scraped_item, parsed_item, vendor, **kwargs):
        if 'colors' not in scraped_item:
            return parsed_item

        mapped_color = self.map_option('color', scraped_item.get('colors', ''))
        mapped_pattern = self.map_option('pattern', scraped_item.get('colors', ''))

        if mapped_color:
            parsed_item['colors'] = mapped_color
        else:
            log.debug('Color mapping failed. Color = %s vendor = %s'
                     % (scraped_item.get('colors'),vendor) )
            self.delete_value(parsed_item, 'colors')

        if mapped_pattern:
            parsed_item['patterns'] = mapped_pattern
        else:
            log.debug('Pattern mapping failed. Pattern = %s vendor = %s'
                     % (scraped_item.get('patterns'),vendor) )
            self.delete_value(parsed_item, 'patterns')

        return parsed_item
