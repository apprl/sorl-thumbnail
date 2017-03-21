# -*- coding: utf-8 -*-
import json
import urlparse
import decimal
import re
import hashlib

from scrapy import signals
from scrapy.exceptions import DropItem
from scrapy.http import Request
from scrapy.contrib.pipeline.images import ImagesPipeline, NoimagesDrop, Image, BytesIO
from django.utils import timezone
from django.core.cache import get_cache
from theimp.models import Product, Vendor
from theimp.parser import Parser
from theimp.utils import get_product_hash, compare_scraped_and_saved
from theimp.tasks import parse_theimp_product
import logging

ASYNC_PARSING = False

log = logging.getLogger("theimp")

cache = get_cache("importer")

class MissingFieldDrop(DropItem):
    """
    Missing field exception
    """


class EmptyFieldDrop(DropItem):
    """
    Empty field exeception
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
    def convert_image(self, image, size=None):
        if image.format == 'PNG' and image.mode == 'RGBA':
            background = Image.new('RGBA', image.size, (255, 255, 255))
            background.paste(image, image)
            image = background.convert('RGB')
        elif image.mode == 'P':
            image = image.convert("RGBA", palette=Image.ADAPTIVE)
            background = Image.new('RGBA', image.size, (255, 255, 255))
            background.paste(image, image)
            image = background.convert('RGB')
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        if size:
            image = image.copy()
            image.thumbnail(size, Image.ANTIALIAS)

        buf = BytesIO()
        image.save(buf, 'JPEG')
        return image, buf


    def file_key(self, url):
        media_guid = hashlib.sha1(url).hexdigest()
        return 'full/%s/%s.jpg' % (media_guid[:2], media_guid)

    def item_completed(self, results, item, info):
        if self.IMAGES_RESULT_FIELD in item.fields:
            item[self.IMAGES_RESULT_FIELD] = [x for ok, x in results if ok]
            if not item[self.IMAGES_RESULT_FIELD]:
                raise NoimagesDrop('Item contains no images')
        return item

class StartImporter:

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()

        #crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)

        return ext

    #def spider_opened(self, spider):
    #    spider.log('Opened spider: {}'.format( spider.name ))

    def spider_closed(self, spider):
        from apparelrow.scheduledjobs.tasks import run_vendor_importer
        from theimp.models import Vendor
        vendor = Vendor.objects.get(name=spider.name)
        spider.log('Closed spider: {} and vendor {}'.format( spider.name, vendor.name ))
        run_vendor_importer.delay(vendor=vendor)


class DatabaseHandler:
    """
    Handles scraped and dropped product updates in database
    """
    scraped_cache_key = "scraped_{id}"
    #semaphore_cache_key = "semaphore_{id}"

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()

        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(ext.item_dropped, signal=signals.item_dropped)

        ext.parser = Parser()

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
                product.is_dropped = True
                product.save()
                spider.log('Dropped item with key: "%s"' % (key,))
            except Product.DoesNotExist:
                spider.log('Could not find dropped item in database with key: "%s"' % (key,))

            if product:
                self.parser.parse(product)

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
        product_hash = get_product_hash(item)

        updated = False
        if product.is_released:
            log.debug('Product %s is released and will not be parsed.' % item['key'])
            return item

        if not created:
            previous_hash = cache.get(self.scraped_cache_key.format(id=product.id))
            if not previous_hash == product_hash:
                updated = True
                json_data = json.loads(product.json)
                log.info("Product {} has been {}.".format(product.id, "updated" if not created else "created"))
                json_data['scraped'].update(dict(item))
                product.json = json.dumps(json_data)
                product.vendor = vendor
                product.is_dropped = False
                product.save()

        if bool(created or updated):
            cache.set(self.scraped_cache_key.format(id=product.id), product_hash, 3600*24*90)
            verb = "updated" if updated else "created"
            log.info('Product {key} is {verb}, parsing will ensue.'.format(key=item["key"], verb=verb))
            if ASYNC_PARSING:
                parse_theimp_product.delay(product.id)
            else:
                self.parser.parse(product)
        else:
            # Todo: Set some date to acknowledge scraping has taken place
            product.parsed_date = timezone.now()
            log.info("Product {key} not updated, only setting a new parsed date.".format(**item))
            product.save(update_fields=['parsed_date'])
        return item


class RequiredFieldsPipeline:
    required_fields = ['key', 'sku', 'name', 'brand',
                       'category', 'gender', 'vendor', 'url', 'affiliate',
                       'regular_price', 'currency','image_urls',
                       'images']

    def __init__(self):
        self.required_fields_value = list(set(self.required_fields) - set(['regular_price', 'discount_price', 'stock', 'colors']))

    def process_item(self, item, spider):
        for field in self.required_fields:
            if field not in item:
                raise MissingFieldDrop('Missing field: %s' % (field,))

        for field in self.required_fields_value:
            if field in item and (item.get(field) == u'' or item.get(field) is None):
                raise EmptyFieldDrop('Empty field: %s' % (field,))

        item['key'] = item['key'].strip()
        item['url'] = item['url'].strip()

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
