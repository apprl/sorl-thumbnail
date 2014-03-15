from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.items import Product
from spiderpig.spiders import AffiliateMixin


class PanosEmporioSpider(CSVFeedSpider, AffiliateMixin):
    name = 'panos-emporio'
    allowed_domains = ['panos.se']
    start_urls = ['http://panos.se/panos/productfeed/google_base_sv.txt']
    delimiter = '\t'

    def parse_row(self, response, row):
        product_url = row.get('product-url').strip()

        item = Product()
        item['key'] = product_url
        if item['key']:
            item['key'] = item['key'].replace('?source=apprl', '')
        item['sku'] = row.get('product-id')
        item['name'] = row.get('product-name')
        item['vendor'] = self.name
        item['url'] = product_url
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('category')
        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = 'M' if 'Herr' in row.get('category') else 'W'
        item['colors'] = ''
        item['regular_price'] = row.get('price').split(' ')[0]
        item['discount_price'] = ''
        item['currency'] = 'SEK'
        item['in_stock'] = True
        item['stock'] = ''
        item['image_urls'] = [row.get('image')]

        return item
