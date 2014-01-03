import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider

from django.utils.encoding import force_bytes

from spiderpig.items import Product
from spiderpig.spiders import AffiliateMixin


key_regex1 = re.compile(r'url\((.+)\)')
key_regex2 = re.compile(r'\?url=(.+)\?tm')


class BubbleroomSpider(CSVFeedSpider, AffiliateMixin):
    name = 'bubbleroom'
    allowed_domains = ['bubbleroom.com']
    start_urls = ['http://pf.tradedoubler.com/export/export?myFeed=13554255561853028&myFormat=12919846971897050']
    delimiter = '|'

    def parse_row(self, response, row):
        # Preprocess
        row.update([x.split(':', 1) for x in row.get('fields', '').split(';') if x])

        item = Product()
        key = key_regex1.search(row.get('productUrl'))
        if key:
            key = urllib.unquote(force_bytes(key.group(1)))
            item['key'] = key_regex2.search(key).group(1)
        item['sku'] = row.get('sku')
        item['name'] = row.get('name')
        item['vendor'] = self.name
        item['url'] = row.get('productUrl')
        item['affiliate'] = self.AFFILIATE_TRADEDOUBLER

        item['category'] = '%s > %s' % (row.get('TDCategoryName'), row.get('merchantCategoryName'))
        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = row.get('merchantCategoryName')
        item['colors'] = item.get('key', '')
        item['regular_price'] = row.get('previousPrice')
        item['discount_price'] = row.get('price')
        item['currency'] = row.get('currency')
        item['in_stock'] = True
        item['stock'] = ''
        item['image_urls'] = [row.get('imageUrl', '').replace('300', '600')]

        return item
