from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


class VrientsSpider(CSVFeedSpider, AffiliateMixin):
    name = 'vrients'
    allowed_domains = ['vrients.com']
    start_urls = ['http://www.vrients.com/media/feed/apprl.csv']
    delimiter = ','

    def parse_row(self, response, row):
        item = Product()
        item['key'] = row.get('link')
        if item['key']:
            item['key'] = item['key'].replace('?source=apprl', '')
        item['sku'] = row.get('id')
        item['name'] = row.get('title')
        item['vendor'] = self.name
        item['url'] = row.get('link')
        item['affiliate'] = self.AFFILIATE_AAN
        bad_words = ['sales', 'view more', 'what\'s new', 'basouk', 'exclusive week-end sale', row.get('brand').lower()]
        item['category'] = ', '.join(x for x in row.get('categories').split(', ') if x.lower() not in bad_words)
        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = 'M'
        item['colors'] = ''
        item['regular_price'] = row.get('price')
        item['discount_price'] = row.get('sale_price')
        item['currency'] = 'EUR'
        item['in_stock'] = True
        item['stock'] = ''
        item['image_urls'] = [row.get('image_link')]

        return item
