import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider

from django.utils.encoding import force_bytes

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


key_regex1 = re.compile(r'url\((.+)\)')


class NellyNOSpider(CSVFeedSpider, AffiliateMixin):
    name = 'nelly-no'
    allowed_domains = ['nelly.com']
    start_urls = ['http://pf.tradedoubler.com/export/export?myFeed=14189174912463884&myFormat=12919846971897050']
    delimiter = '|'

    def parse_rows(self, response):
        response = response.replace(encoding='iso-8859-1')
        return super(NellyNOSpider, self).parse_rows(response)

    def parse_row(self, response, row):
        # Preprocess
        row.update([x.split(':', 1) for x in row.get('fields', '').split(';') if x])

        in_stock = row.get('inStock')
        stock = 0
        if in_stock:
            try:
                stock = int(in_stock)
            except ValueError:
                pass

        item = Product()
        key = key_regex1.search(row.get('productUrl'))
        if key:
            item['key'] = urllib.unquote(force_bytes(key.group(1)))
        item['sku'] = row.get('TDProductId')
        item['name'] = row.get('name')
        item['vendor'] = self.name
        item['url'] = row.get('productUrl')
        item['affiliate'] = self.AFFILIATE_TRADEDOUBLER

        item['category'] = '%s > %s' % (row.get('TDCategoryName'), row.get('merchantCategoryName'))
        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = row.get('gender')
        item['colors'] = row.get('color')
        item['regular_price'] = row.get('previousPrice')
        item['discount_price'] = row.get('price')
        item['currency'] = row.get('currency')
        item['in_stock'] = True if stock > 0 else False
        item['stock'] = stock
        item['image_urls'] = [row.get('extraImageProductLarge', '').replace('productLarge', 'productPress')]

        return item
