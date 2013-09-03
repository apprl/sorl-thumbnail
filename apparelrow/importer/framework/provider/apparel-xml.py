import logging

from lxml import etree

from apparelrow.importer.framework.provider import Provider as BaseProvider
from apparelrow.importer.framework.mapper import DataMapper

logger = logging.getLogger('apparel.importer')

class ApparelMapper(DataMapper):
    def get_variations(self):
        for v in self.record['variations']:
            if 'color' in v:
                c = self.map_colors(v['color'])
                if len(c):
                    v['color'] = c[0]
                else:
                    logger.debug('Color %s not recogised' % v['color'])
                    del v['color']

            if 'in-stock' in v:
                try:
                    v['availability'] = int(v['in-stock'])
                    del v['in-stock']
                except ValueError:
                    pass

        return self.record['variations']

    def get_image_url(self):
        return [(self.record.get('image-url'), self.IMAGE_MEDIUM)]

    def get_availability(self):
        availability_sum = 0
        for v in self.get_variations():
            if 'availability' in v:
                if v['availability'] > 0:
                    availability_sum += v['availability']

        if availability_sum > 0:
            return -1
        elif availability_sum == 0:
            return 0

        return None

    def get_category(self):
        gender = self.record.get('gender')
        if gender:
            return '%s > %s' % (gender, self.record.get('category'))

        return self.record.get('category')


class Provider(BaseProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.extension = 'xml'
        self.mapper=ApparelMapper


    def process(self):
        doc = etree.parse(self.file)
        for p in doc.xpath('//product'):
            record = dict([
                (e.tag, e.text)
                for e in p.xpath('./*')
            ])

            record['variations'] = []
            for v in p.xpath('./variations/*'):
                record['variations'].append(dict(v.attrib))

            record = self.mapper(self, record).translate()
            self.import_data(record)
