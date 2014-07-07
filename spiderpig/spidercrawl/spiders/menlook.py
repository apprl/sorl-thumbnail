from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


class SsenseSpider(CSVFeedSpider, AffiliateMixin):
    name = 'menlook'
    allowed_domains = ['menlook.com']
    start_urls = ['http://flux.lengow.com/shopbot/apprl/60001/txt/']
    delimiter = '|'

    def parse_row(self, response, row):
        item = Product()
        item['key'] = row.get('link')
        item['sku'] = row.get('item group id')
        item['name'] = row.get('title')
        item['vendor'] = self.name
        item['url'] = row.get('link')
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = '%s > %s > %s' % (row.get('age group'),
                                             row.get('gender'),
                                             row.get('google product category'))
        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = row.get('gender')
        item['colors'] = row.get('color')
        item['regular_price'] = row.get('sale price')
        item['discount_price'] = row.get('price')
        item['currency'] = 'GBP'
        item['in_stock'] = True if row.get('availability') == 'in stock' else False
        item['stock'] = ''
        item['image_urls'] = [row.get('image link', '?').split('?', 1)[0]]

        return item
