# -*- coding: utf-8 -*-
import json
import urlparse
import decimal
import re
import hashlib

from scrapy import signals
from scrapy.exceptions import DropItem
from scrapy.http import Request
from scrapy.contrib.pipeline.images import ImagesPipeline, NoimagesDrop

from hotqueue import HotQueue

from apparelrow import settings
from theimp.models import Product, Vendor


class MissingFieldDrop(DropItem):
    """
    Missing field exception
    """


class CustomImagesPipeline(ImagesPipeline):
    """
    Save images to path vendor/hash.
    """
    #CONVERTED_ORIGINAL = re.compile(r'^full/[0-9,a-f]+.jpg$')


    #def get_images(self, response, request, info):
        #for key, image, buf, in super(CustomImagesPipeline, self).get_images(response, request, info):
            #if self.CONVERTED_ORIGINAL.match(key):
                #key = self.change_key(key, request.meta)
            #yield key, image, buf

    #def get_media_requests(self, item, info):
        #return [Request(x, meta={'vendor': item.get('vendor')}) for x in item.get(self.IMAGES_URLS_FIELD, [])]

    #def change_key(self, key, meta):
        #return key.replace('full', request.meta.get('vendor'))

    def file_key(self, url):
        media_guid = hashlib.sha1(url).hexdigest()
        return 'full/%s/%s.jpg' % (media_guid[:2], media_guid)

    def item_completed(self, results, item, info):
        if self.IMAGES_RESULT_FIELD in item.fields:
            item[self.IMAGES_RESULT_FIELD] = [x for ok, x in results if ok]
            if not item[self.IMAGES_RESULT_FIELD]:
                raise NoimagesDrop('Item contains no images')
        return item


class DatabaseHandler:
    """
    Handles scraped and dropped product updates in database
    """
    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()

        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(ext.item_dropped, signal=signals.item_dropped)

        ext.parse_queue = HotQueue(settings.THEIMP_QUEUE_PARSE,
                                   host=settings.THEIMP_REDIS_HOST,
                                   port=settings.THEIMP_REDIS_PORT,
                                   db=settings.THEIMP_REDIS_DB)

        return ext

    def _is_valid_url(self, url):
        parsed_url = urlparse.urlparse(url)

        if parsed_url.netloc and \
                (parsed_url.scheme == 'http' or parsed_url.scheme == 'https'):
            return True

        return False

    def spider_opened(self, spider):
        spider.log('Opened spider: %s' % spider.name)

    def spider_closed(self, spider):
        spider.log('Closed spider: %s' % spider.name)

    def item_dropped(self, item, spider):
        """
        Updated database with dropped item.
        """
        key = item.get('key', None)
        if key:
            product = None
            try:
                product = Product.objects.get(key=key)
                product.dropped = True
                product.save()
                spider.log('Dropped item with key: "%s"' % (key,))
            except Product.DoesNotExist:
                spider.log('Could not find dropped item in database with key: "%s"' % (key,))

            if product:
                self.parse_queue.put(product.pk)

    def item_scraped(self, item, spider):
        """
        Updated database with scraped item.
        """
        data = {
            'scraped': dict(item),
            'parsed': {},
            'final': {},
        }
        json_string = json.dumps(data)

        vendor, _ = Vendor.objects.get_or_create(name=item['vendor'])
        product, created = Product.objects.get_or_create(key=item['key'], defaults={'json': json_string, 'vendor': vendor})
        if not created:
            json_data = json.loads(product.json)
            json_data['scraped'].update(dict(item))
            product.json = json.dumps(json_data)
            product.vendor = vendor
            product.dropped = False
            product.save()

        self.parse_queue.put(product.pk)

        return item


class RequiredFieldsPipeline:
    required_fields = ['key', 'name', 'vendor', 'url']

    def process_item(self, item, spider):
        for field in self.required_fields:
            if not item.get(field, None):
                raise MissingFieldDrop('Missing field: %s' % (field,))

        return item


class PricePipeline:

    currency_map = {
        'kr': 'SEK'
    }

    def parse_price(self, price_string):
        """
        Parse a price string to a decimal price and a possible three letter
        currency.
        """
        if not price_string:
            return (None, None)

        if price_string.isalpha():
            return (None, None)

        if price_string.isdigit():
            return (decimal.Decimal(price_string), None)

        price_string = re.sub(r',(\d\d)(?![^ ])', r'.\1', price_string)
        price_first, _, price_second = price_string.rpartition('.')
        price_first = price_first.replace('.', '')
        if price_first:
            price_string = ''.join([price_first, '.', price_second])
        else:
            price_string = price_second

        currency = []
        price = []
        for token in list(price_string):
            if token.isalpha():
                currency.append(token)
            elif token.isdigit():
                price.append(token)
            elif token == '.':
                price.append(token)
            elif token == u'€':
                del currency[:]
                currency.append('EUR')
            elif token == u'$':
                del currency[:]
                currency.append('USD')
            elif token == u'£':
                del currency[:]
                currency.append('GBP')

        try:
            price = decimal.Decimal(''.join(price))
        except decimal.InvalidOperation:
            return (None, None)

        currency = ''.join(currency)
        if currency in self.currency_map:
            currency = self.currency_map[currency]

        if len(currency) != 3:
            currency = None

        return (price, currency)

    def process_item(self, item, spider):
        regular_price = item.get('regular_price', None)
        discount_price = item.get('discount_price', None)
        currency = item.get('currency', None)

        regular_price, regular_currency = self.parse_price(regular_price)
        discount_price, discount_currency = self.parse_price(discount_price)

        if not regular_price and not discount_price:
            return item

        if discount_price and not regular_price:
            item['regular_price'] = str(discount_price)
            item['discount_price'] = None
        else:
            item['regular_price'] = str(regular_price)
            item['discount_price'] = str(discount_price)

        currency_list = [currency, regular_currency, discount_currency]
        item['currency'] = next((x for x in currency_list if x), None)

        return item
