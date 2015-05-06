import re

from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


class GinaTricotSpider(CSVFeedSpider, AffiliateMixin):
    name = 'ginatricot'
    allowed_domains = ['ginatricot.com',]
    start_urls = ['http://www.ginatricot.com/googleshoppingfeed_SE.csv']
    delimiter = '|'
    headers = (
        'id',
        'brand',
        'title',
        'product_type',
        'description',
        'link',
        'condition',
        'price',
        'availability',
        'image link',
        'gender',
        'custom_label_0',
        'custom_label_1',
    )

    def parse_row(self, response, row):
        item = Product()
        item['key'] = row.get('link')
        item['sku'] = row.get('id')
        item['name'] = row.get('title')
        item['vendor'] = self.name
        item['url'] = row.get('link')
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('product_type')
        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = row.get('gender')
        item['colors'] = row.get('title') + row.get('description')
        item['regular_price'] = row.get('price')
        item['discount_price'] = row.get('price')
        item['currency'] = 'SEK'
        item['in_stock'] = True if row.get('availability').lower() == 'in stock' else False
        item['stock'] = ''
        item['image_urls'] = [row.get('image link')]

        return item
