import logging
import collections

import xmltodict

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from apparelrow.importer.framework.mapper import DataMapper
from apparelrow.importer.framework.provider.aan import Provider as AanProvider
from apparelrow.importer.api import SkipProduct

from advertiser.utils import make_advertiser_url

logger = logging.getLogger('apparel.importer')


class OddMollyMapper(DataMapper):
    def get_product_id(self):
        if self.record.get('g:age_group', '').lower() != 'adult':
            raise SkipProduct('Not adult product')

        return self.record.get('g:id')

    def get_product_name(self):
        return self.record.get('title')

    def get_description(self):
        return self.record.get('description')

    def get_manufacturer(self):
        return self.record.get('g:brand')

    def get_product_url(self):
        try:
            store_id = self.provider.feed.vendor.store.get().identifier
        except (MultipleObjectsReturned, ObjectDoesNotExist, AttributeError):
            logger.error('Could not get store identifier, check that a store id exists and is linked to vendor')
            store_id = 'unknown'

        return make_advertiser_url(store_id, self.record.get('link'))

    def get_category(self):
        return '%s > %s' % (self.get_gender(), self.record.get('g:product_type'))

    def get_gender(self):
        return self.map_gender(self.record.get('g:gender', ''))

    def get_price(self):
        return self.record.get('g:price', '').rsplit(' ', 1)[0]

    def get_discount_price(self):
        return self.record.get('g:sale_price', '').rsplit(' ', 1)[0]

    def get_currency(self):
        return self.record.get('g:price').rsplit(' ', 1)[1]

    def get_image_url(self):
        image = self.record.get('g:image_link')
        return [(image, self.IMAGE_LARGE)]

    def get_availability(self):
        if self.record.get('g:availability', '').lower() == 'in stock':
            return -1

        return 0

    def get_color(self):
        return self.map_colors(self.record.get('g:color', ''))

    def get_variations(self):
        availability = self.get_availability()
        colors = self.get_color()

        variations = []
        for color in colors:
            if color:
                variations.append({'color': color, 'size': None, 'availability': availability})

        return variations


class Provider(AanProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.extension = 'xml'
        self.mapper=OddMollyMapper

    def process(self):
        content = self.file.read()
        xml_dict = xmltodict.parse(content)

        duplicate_storage = {}
        for row in xml_dict['rss']['channel']['item']:
            try:
                record = self.mapper(self, row).translate()
            except SkipProduct, e:
                logger.info('Skipped product during mapping: %s' % (e,))
                continue

            duplicate_key = row.get('g:item_group_id') or row.get('g:id')
            duplicate_key = (duplicate_key, row.get('g:color'))
            if duplicate_key in duplicate_storage:
                logger.info('merge duplicate %s' % (duplicate_key,))
                self.merge_duplicate(duplicate_storage[duplicate_key], record)
            else:
                duplicate_storage[duplicate_key] = record

        for key, record in duplicate_storage.items():
            self.import_data(record)

    def merge_duplicate(self, stored_record, new_record):
        pass
