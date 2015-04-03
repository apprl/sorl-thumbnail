import re

from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


key_regex1 = re.compile(r'\?url=(.+)$')

class CareOfCarlSpider(CSVFeedSpider, AffiliateMixin):
    name = 'care-of-carl'
    allowed_domains = ['http://careofcarl.com/']
    start_urls = ['http://admin.careofcarl.com/agent/pricerunner_NOK_SV.txt']
    delimiter = '\t'
    headers = (
        'Category',
        'ProductID',
        'Price',
        'Product link',
        'Product name',
        'ProductID',
        'Manufacturer',
        '',
        '',
        'Product description',
        'Product image',
        '',
        'Availability',
        '',
        '',
        'Delivery time',
        '',
    )

    def parse_rows(self, response):
        response = response.replace(encoding='iso-8859-1')
        return super(CareOfCarlSpider, self).parse_rows(response)

    def parse_row(self, response, row):
        item = Product()
        item['key'] = row.get('Product link')
        item['sku'] = row.get('ProductID')
        item['name'] = row.get('Product name')
        item['vendor'] = self.name
        item['url'] = row.get('Product link')
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('Category')
        item['description'] = row.get('Product description')
        item['brand'] = row.get('Manufacturer')
        item['gender'] = 'M'
        item['colors'] = row.get('Product name') + row.get('Product description')
        item['regular_price'] = row.get('Price')
        item['discount_price'] = item['regular_price']
        item['currency'] = 'SEK'
        item['in_stock'] = row.get('In Stock') == 'Ja'
        item['stock'] = '-'
        item['image_urls'] = [row.get('Product image', '')]
        return item