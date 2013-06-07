import logging
import collections

import xmltodict

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import get_model

from apparelrow.importer.framework.provider.aan import Provider as AanProvider, AanMapper

from advertiser.utils import make_advertiser_url

logger = logging.getLogger('apparel.importer')


class VrientsMapper(AanMapper):
    def get_product_id(self):
        return self.record.get('@id')

    def get_product_name(self):
        return self.record.get('name')

    def get_description(self):
        return self.record.get('description')

    def get_manufacturer(self):
        return self.record.get('brand')

    def get_product_url(self):
        try:
            store_id = self.provider.feed.vendor.store.get().identifier
        except (MultipleObjectsReturned, ObjectDoesNotExist, AttributeError):
            logger.error('Could not get store identifier, check that a store id exists and is linked to vendor')
            store_id = 'unknown'

        return make_advertiser_url(store_id, self.record.get('link'))

    def get_category(self):
        categories = self.record.get('categories')
        if categories:
            category_list = categories.get('category')
            if not isinstance(category_list, list):
                category_list = [category_list]

            merged_categories = collections.OrderedDict()
            for category in category_list:
                for category_part in category.split(' - '):
                    merged_categories[category_part] = 1

            return ' / '.join(merged_categories.keys())

        return 'Unknown'

    def get_gender(self):
        return self.map_gender(self.record.get('name', '') + self.record.get('description', ''))

    def get_price(self):
        return self.record.get('price').get('#text')

    def get_currency(self):
        return self.record.get('price').get('@currency')

    def get_image_url(self):
        images = self.record.get('images')
        if images:
            image = images.get('image')[0].get('@url')

            return [(image, self.IMAGE_LARGE)]

        return []

    def get_availability(self):
        return None

    def get_color(self):
        return self.map_colors(self.record.get('description', ''))

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
        self.mapper=VrientsMapper

    def process(self):
        content = self.file.read()
        xml_dict = xmltodict.parse(content)

        for record in xml_dict['products']['product']:
            record = self.mapper(self, record).translate()
            self.import_data(record)
