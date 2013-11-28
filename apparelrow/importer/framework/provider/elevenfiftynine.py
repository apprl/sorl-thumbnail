import logging

import xmltodict

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from apparelrow.importer.framework.mapper import DataMapper
from apparelrow.importer.framework.provider.aan import Provider as AanProvider
from apparelrow.importer.api import SkipProduct

from advertiser.utils import make_advertiser_url

logger = logging.getLogger('apparel.importer')


class ElevenfiftynineMapper(DataMapper):
    def get_product_id(self):
        return self.record.get('supplier_reference') or ''

    def get_product_name(self):
        return self.record.get('descriptions').get('descriptions-en').get('name-en')

    def get_description(self):
        return self.record.get('descriptions').get('descriptions-en').get('description-en') or ''

    def get_manufacturer(self):
        return self.record.get('manufacturer_name')

    def get_product_url(self):
        try:
            store_id = self.provider.feed.vendor.store.get().identifier
        except (MultipleObjectsReturned, ObjectDoesNotExist, AttributeError):
            raise SkipProduct('Could not get store identifier, check that a store id exists and is linked to vendor')

        return make_advertiser_url(store_id, self.record.get('product_url'))

    def get_category(self):
        return self.record.get('default_category').get('category_default_name-en')

    def get_gender(self):
        return self.map_gender('')

    def get_price(self):
        return self.record.get('price_sale')

    def get_discount_price(self):
        return None

    def get_currency(self):
        return 'SEK'

    def get_image_url(self):
        image = self.record.get('images')
        if image:
            image = image.get('thickbox')
            return [(image, self.IMAGE_LARGE)]

        return None

    def get_availability(self):
        if self.record.get('active') == '1':
            return -1

        return 0

    def get_color(self):
        return self.map_colors(self.record.get('descriptions').get('descriptions-en').get('name-en'))

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
        self.mapper=ElevenfiftynineMapper

    def process(self):
        content = self.file.read()
        xml_dict = xmltodict.parse(content)

        #duplicate_storage = {}
        for row in xml_dict['products']['product']:
            try:
                record = self.mapper(self, row).translate()
            except SkipProduct, e:
                logger.info('Skipped product during mapping: %s' % (e,))
                continue

            self.import_data(record)

            #duplicate_key = row.get('g:item_group_id') or row.get('g:id')
            #duplicate_key = (duplicate_key, row.get('g:color'))
            #if duplicate_key in duplicate_storage:
                #logger.info('merge duplicate %s' % (duplicate_key,))
                #self.merge_duplicate(duplicate_storage[duplicate_key], record)
            #else:
                #duplicate_storage[duplicate_key] = record

        #for key, record in duplicate_storage.items():
            #self.import_data(record)

    #def merge_duplicate(self, stored_record, new_record):
        #pass
