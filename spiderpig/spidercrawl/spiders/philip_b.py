from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


class PhilipBSpider(CSVFeedSpider, AffiliateMixin):
    name = 'philip-b'
    allowed_domains = ['www.philipb.com']
    start_urls = ['http://www.philipb.com/products.txt']
    delimiter = '\t'

    def parse_row(self, response, row):
        product_url = row.get('Product URL').strip()
        item = Product()
        item['key'] = product_url
        item['sku'] = row.get('Product ID')
        item['name'] = row.get('Product Name')
        item['vendor'] = self.name
        item['url'] = product_url
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('Product Category')
        item['description'] = row.get('Product Text Description')
        item['brand'] = row.get('Brand Name')
        item['gender'] = 'U'
        item['colors'] = 'white'
        item['regular_price'] = row.get('Price')
        item['discount_price'] = ''
        item['currency'] = 'USD'
        item['in_stock'] = True
        item['stock'] = '-'
        item['image_urls'] = [row.get('Image URL')]

        return item
