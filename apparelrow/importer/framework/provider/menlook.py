# -*- coding: utf-8 -*-
import urllib

from django.core.urlresolvers import reverse

from apparelrow.importer.framework.provider import CSVProvider
from apparelrow.importer.framework.parser import utils
from apparelrow.importer.framework.mapper import DataMapper
from apparelrow.importer.api import SkipProduct

class MenlookMapper(DataMapper):

    def get_product_id(self):
        if self.record.get('age group', '').lower() != 'adult':
            raise SkipProduct('Not adult product')

        return self.record['item group id']

    def get_product_name(self):
        return self.record['title']

    def get_description(self):
        return self.record['description']

    def get_manufacturer(self):
        return self.record['brand']

    def get_gender(self):
        return self.map_gender(self.record.get('gender', ''))

    def get_availability(self):
        availability = self.record.get('availability', '')
        if availability == 'in stock':
            return -1

        return 0

    def get_product_url(self):
        quoted_link = urllib.quote(self.record['link'], '')
        return 'http://apprl.com%s?store_id=menlook&url=%s' % (reverse('advertiser-link'), quoted_link)

    def get_category(self):
        return '%s > %s' % (self.get_gender(), self.record.get('google product category'))

    def get_image_url(self):
        image_url = self.record.get('image link', '')
        image_url = image_url.split('?', 1)[0]
        return  [(image_url, self.IMAGE_MEDIUM)]

    def get_price(self):
        return self.record['price']

    def get_discount_price(self):
        if self.record['sale price'] != self.record['price']:
            return self.record['sale price']

        return None

    def get_currency(self):
        return 'GBP'

    def get_variations(self):
        return [{'color': c} for c in self.map_colors(self.record.get('color', ''))]


class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=MenlookMapper
        self.encoding='latin-1'
        self.dialect=utils.CSVPipeDelimited
        self.unique_fields=['product-id']
