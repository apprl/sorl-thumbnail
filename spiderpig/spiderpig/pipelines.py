import json
import urlparse

from scrapy import signals
from scrapy.exceptions import DropItem

from theimp.models import Product, Vendor


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

        return ext

    def _is_valid_url(self, url):
        parsed_url = urlparse.urlparse(url)

        if parsed_url.netloc and \
                (parsed_url.scheme == 'http' or parsed_url.scheme == 'https'):
            return True

        return False

    def spider_opened(self, spider):
        self.vendor, created = Vendor.objects.get_or_create(name=spider.name)
        query = 'SELECT id, key FROM theimp_product WHERE vendor_id = %s'
        products = Product.objects.raw(query, [self.vendor.pk])
        product_urls = [x.key for x in products if self._is_valid_url(x.key)]

        spider.start_urls = product_urls + spider.start_urls
        spider.log('Opened spider: %s' % spider.name)

    def spider_closed(self, spider):
        spider.log('Closed spider: %s' % spider.name)

    def item_dropped(self, item, spider):
        """
        Updated database with dropped item.
        """
        key = item.get('key', None)
        if key:
            try:
                product = Product.objects.get(key=key)
                product.dropped = True
                product.save()
                spider.log('Dropped item with key: "%s"' % (key,))
            except Product.DoesNotExist:
                spider.log('Could not find dropped item in database with key: "%s"' % (key,))

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
            json_data['parsed'] = dict(item)
            product.json = json.dumps(json_data)
            product.dropped = False
            product.save()

        return item


class RequiredFieldsPipeline:
    required_fields = ['key', 'name', 'vendor', 'brand', 'url', 'category', 'price']

    def process_item(self, item, spider):
        for field in self.required_fields:
            if not item.get(field, None):
                raise DropItem('Missing field: %s' % (field,))

        return item


class PricePipeline:

    # TODO: not satisified with this pipeline, how could we differentiate
    # between price and discount price in a generic way?
    def process_item(self, item, spider):
        price = item.get('price', None)
        regular_price = item.get('regular_price', None)
        discount_price = item.get('discount_price', None)
        currency = item.get('currency', None)
        in_stock = item.get('in_stock', None)

        if price:
            price_parts = price.rsplit(' ', 1)
            if len(price_parts) == 1 and not currency:
                raise DropItem('Missing currency in %s' % item)

            if len(price_parts[1]) != 3:
                raise DropItem('Could not parse currency some price in %s' % item)

            # TODO: better handling of currency?

            item['price'] = price_parts[0]
            item['currency'] = price_parts[1]

            if regular_price:
                item['regular_price'] = regular_price.rsplit(' ', 1)[0]

            if discount_price:
                item['discount_price'] = discount_price.rsplit(' ', 1)[0]

            return item
        elif in_stock == False:
            item['price'] = u''
            item['currency'] = u''

            return item
        else:
            raise DropItem('Missing price and no in_stock information in %s' % item)
