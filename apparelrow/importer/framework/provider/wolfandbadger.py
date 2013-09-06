# -*- coding: utf-8 -*-
import logging

from lxml import etree

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from apparelrow.importer.framework.provider import Provider as BaseProvider
from apparelrow.importer.framework.mapper import DataMapper

from advertiser.utils import make_advertiser_url

logger = logging.getLogger('apparel.importer')


class WolfAndBadgerMapper(DataMapper):

    def get_product_id(self):
        return self.record.get('id')

    def get_product_name(self):
        return self.record.get('title').split(' - ', 1)[-1]

    def get_manufacturer(self):
        return self.record.get('title').split(' - ', 1)[0]

    def get_description(self):
        return self.record.get('description')

    def get_gender(self):
        return self.map_gender(self.record.get('product_type'))

    def get_availability(self):
        return self.record.get('availability') == 'in stock'

    def get_product_url(self):
        return make_advertiser_url(self.provider.store_id, self.record.get('link'))

    def get_category(self):
        return '%s > %s' % (self.get_gender(), self.record.get('product_type'))

    def get_image_url(self):
        return  [(self.record.get('image_link', [None])[0], self.IMAGE_MEDIUM)]

    def get_price(self):
        return self.record.get('price')

    def get_discount_price(self):
        return self.record.get('sale_price')

    def get_currency(self):
        return 'GBP'


class Provider(BaseProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.extension = 'xml'
        self.mapper = WolfAndBadgerMapper

        try:
            self.store_id = self.feed.vendor.store.get().identifier
        except (MultipleObjectsReturned, ObjectDoesNotExist, AttributeError):
            logger.error('Could not get store identifier, check that a store id exists and is linked to vendor')
            self.store_id = 'unknown'

    def process(self):
        doc = etree.parse(self.file)
        for p in doc.xpath('//ns:entry', namespaces={'ns': 'http://www.w3.org/2005/Atom'}):
            record = dict([
                (e.tag.rsplit('}', 1)[-1], e.text)
                for e in p.xpath('./*')
            ])

            record['link'] = p.xpath('./ns:link', namespaces={'ns': 'http://www.w3.org/2005/Atom'})[0].attrib.get('href')
            record['image_link'] = [x.text for x in p.xpath('./ns:image_link', namespaces={'ns': 'http://base.google.com/ns/1.0'})]

            record = self.mapper(self, record).translate()
            self.import_data(record)
