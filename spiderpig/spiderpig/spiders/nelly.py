import re

from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.spiders import CSVFeedSpider
from scrapy.http import Request

from spiderpig.items import Product, ProductLoader
from spiderpig.spiders import AffiliateMixin


class NellySpider(CSVFeedSpider, AffiliateMixin):
    name = 'nelly'
    allowed_domains = ['nelly.com']
    start_urls = ['http://pf.tradedoubler.com/export/export?myFeed=13164639121853028&myFormat=12919846971897050']
    delimiter = '|'

    def parse_row(self, response, row):
        # Preprocess
        row.update([x.split(':', 1) for x in row.get('fields', '').split(';') if x])

        item = Product()
        item['key'] = row.get('productUrl') # TODO: remove tradedoubler tracking
        item['sku'] = row.get('sku')
        item['name'] = row.get('name')
        item['vendor'] = self.name
        item['url'] = row.get('productUrl')
        item['affiliate'] = self.AFFILIATE_TRADEDOUBLER

        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = row.get('gender')
        item['regular_price'] = row.get('previousPrice')
        item['discount_price'] = row.get('price')
        item['currency'] = row.get('currency')
        item['in_stock'] = True if int(row.get('inStock', 0)) > 0 else False
        item['image_urls'] = [row.get('extraImageProductLarge', '').replace('productLarge', 'productPress')]

        # Replace the return item statement with this to fetch and parse the product page
        #return [item, Request(item['key'], callback=self.parse_item)]
        return item

    #def parse_item(self, response):
        #yield None
