import logging
import collections

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from apparelrow.importer.framework.mapper import DataMapper
from apparelrow.importer.framework.provider import CSVProvider

from advertiser.utils import make_advertiser_url

logger = logging.getLogger('apparel.importer')


class VrientsMapper(DataMapper):
    def get_product_id(self):
        return self.record.get('id')

    def get_product_name(self):
        return self.record.get('title')

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
        bad_words = ['sales', 'view more', 'what\'s new', 'basouk', 'exclusive week-end sale', self.get_manufacturer().lower()]
        return ', '.join(x for x in self.record.get('categories').split(', ') if x.lower() not in bad_words)

    def get_gender(self):
        return 'M'

    def get_price(self):
        return self.record.get('price')

    def get_discount_price(self):
        return self.record.get('sale_price')

    def get_currency(self):
        return 'EUR'

    def get_image_url(self):
        return [(self.record.get('image_link'), self.IMAGE_LARGE)]

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


class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=VrientsMapper
