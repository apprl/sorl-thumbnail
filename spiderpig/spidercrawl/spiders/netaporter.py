import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider
from scrapy.http import Request

from django.utils.encoding import force_bytes

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


key_regex1 = re.compile(r'murl=(.+)')


class NetAPorterSpider(CSVFeedSpider, AffiliateMixin):
    name = 'net-a-porter'
    allowed_domains = ['netaporter.com']
    start_urls = ['ftp://aftp.linksynergy.com/24448_2648039_mp.txt.gz']
    delimiter = '|'
    headers = (
            'product-id',
            'product-name',
            'sku',
            'category',
            'secondary-category',
            'product-url',
            'image-url',
            'buy-url',
            'description',
            'long-description',
            'discount',
            'discount-type',
            'discount-price',       # Sale price, includes discount
            'retail-price',
            'available-from',
            'available-to',
            'brand',
            'delivery-price',
            'keywords',             # ~~ delimited
            'manufacturer-part-no',
            'manufacturer',
            'shipping-information',
            'availability',
            'universal-product-code',
            'classification-id',
            'currency',
            'm1',                   # blank field
            'tracking-pixel-url',
            'miscellaneous-attribute',
            'attribute2',
            'size',                 # attribute 3
            'material',             # attribute 4
            'color',
            'gender',
            'type',                 # attribute 7
            'agegroup',
            'attribute9',
            'attribute10',
        )

    """def __init__(self, name=None, **kwargs):
        from spiderpig.utils import ApprlFileLogObserver
        from scrapy import log
        from scrapy.log import INFO
        loglevel = INFO
        file_to_write = open('%s.log' % self.name,'a')
        logencoding = "utf-8"
        crawler = name
        sflo = ApprlFileLogObserver(file_to_write, loglevel, logencoding, crawler)
        log.log.addObserver(sflo.emit)
        super(NetAPorterSpider, self).__init__(name, **kwargs)
"""

    def start_requests(self):
        meta = {'ftp_user': 'apparelrow', 'ftp_password': 'fdzfdFiJ'}
        for url in self.start_urls:
            yield Request(url, meta=meta, dont_filter=True)

    def parse_row(self, response, row):
        from scrapy import log
        from scrapy.log import INFO
        item = Product()
        key = key_regex1.search(row.get('product-url'))
        #log.msg('Input [%s] Output [%s]' % (row.get('product-url'),key.group(1)),INFO)
        #print key
        if key:
            item['key'] = urllib.unquote(force_bytes(key.group(1)))
            item['key'] = item['key'].split('?', 1)[0]
        item['sku'] = row.get('product-id')
        item['name'] = row.get('product-name')
        item['vendor'] = self.name
        item['url'] = row.get('product-url')
        item['affiliate'] = self.AFFILIATE_LINKSHARE
        item['category'] = '%s > %s > %s' % (row.get('gender'), row.get('category'), row.get('secondary-category'))
        item['description'] = row.get('description')
        item['brand'] = row.get('manufacturer') or row.get('brand')
        item['gender'] = row.get('gender')
        item['colors'] = row.get('color')
        item['regular_price'] = row.get('retail-price')
        item['discount_price'] = row.get('discount-price') or row.get('retail-price')
        item['currency'] = row.get('currency')
        item['in_stock'] = True #Not working anymoreif row.get('availability', '').lower() == 'in stock' else False
        item['stock'] = '10'
        item['image_urls'] = [row.get('image-url').replace("in_l","in_xl") if row.get('image-url',None) else '']

        return item
