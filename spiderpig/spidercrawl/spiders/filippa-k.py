import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider
from scrapy.http import Request

from django.utils.encoding import force_bytes

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


key_regex1 = re.compile(r'\[\[(.+)\]\]')


class FilippaKSpider(CSVFeedSpider, AffiliateMixin):
    name = 'filippa-k'
    allowed_domains = ['filippa-k.com']
    start_urls = ['http://www.filippa-k.com/var/feeds/apprl.csv']
    delimiter = ','
    headers = (
        'product-id',
        'product-name',
        'category',
        'brand',
        'price',
        'sale-price',   # Sale price, includes discount
        'currency',
        'product-url',
        'image-url',
        'description',
        'color',
        'size',
        'in-stock',
        'amount-in-stock',
    )

    def parse_row(self, response, row):
        item = Product()
        item['key'] = row.get('product-url')
        item['sku'] = row.get('product-id')
        item['name'] = row.get('product-name')
        item['vendor'] = self.name
        item['url'] = row.get('product-url')
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('category')
        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = row.get('category')
        item['colors'] = row.get('color')
        item['regular_price'] = row.get('price')
        item['discount_price'] = row.get('sale-price')
        item['currency'] = row.get('currency')
        item['in_stock'] = True if row.get('in-stock').lower() == 'yes' else False
        item['stock'] = row.get('amount-in-stock')
        item['image_urls'] = [row.get('image-url')]

        return item
