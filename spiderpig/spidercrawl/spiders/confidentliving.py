import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider
from scrapy.http import Request

from django.utils.encoding import force_bytes

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


key_regex1 = re.compile(r'\?url=(.+)$')

class ConfidentLivingSpider(CSVFeedSpider, AffiliateMixin):
    name = 'confident-living'
    allowed_domains = ['http://confidentliving.se/']
    start_urls = ['ftp://ftp.enferno.se/confidentliving.txt']
    delimiter = '\t'
    headers = (
        'Category',
        'SKU',
        'Price',
        'Product URL',
        'Product name',
        'Manufacturer SKU',
        'Manufacturer',
        'EAN',
        'ISBN',
        'Description',
        'Graphic URL',
        'Catalog Id',
        'In Stock',
        'Stock Level',
        'Delivery time',
        'Shipping Cost'
    )


    def parse_rows(self, response):
        response = response.replace(encoding='iso-8859-1')
        return super(ConfidentLivingSpider, self).parse_rows(response)


    def start_requests(self):
        meta = {'ftp_user': 'CL_Pricerunner', 'ftp_password': 'ESM9onUf'}
        for url in self.start_urls:
            yield Request(url, meta=meta, dont_filter=True)

    def parse_row(self, response, row):
        item = Product()
        item['key'] = row.get('Product URL')
        item['sku'] = row.get('SKU')
        item['name'] = row.get('Product name')
        item['vendor'] = self.name
        item['url'] = row.get('Product URL')
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('Category')
        item['description'] = row.get('Description')
        item['brand'] = row.get('Manufacturer')
        item['gender'] = 'U'
        item['colors'] = row.get('Product name') + row.get('Description')
        item['regular_price'] = row.get('Price')
        item['discount_price'] = item['regular_price']
        item['currency'] = 'SEK'
        item['in_stock'] = row.get('In Stock') == 'Ja'
        item['stock'] = row.get('Stock Level') or 10
        item['image_urls'] = [row.get('Graphic URL', '')]
        return item