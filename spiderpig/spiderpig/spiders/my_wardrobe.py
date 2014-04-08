import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider
from scrapy.http import Request
from django.utils.encoding import force_bytes
from spiderpig.items import Product
from spiderpig.spiders import AffiliateMixin

key_regex1 = re.compile(r'murl=(.+)')


class MyWardrobeSpider(CSVFeedSpider, AffiliateMixin):
    name = 'my-wardrobe'
    allowed_domains = ['my-wardrobe.com']
    start_urls = ['ftp://aftp.linksynergy.com/39116_2648039_mp.txt.gz']
    delimiter = '|'
    headers = (
            'product-id',#1
            'product-name',
            'sku',
            'category',
            'secondary-category',#5
            'product-url',
            'image-url',
            'buy-url',
            'description',
            'long-description',#10
            'discount',
            'discount-type',
            'discount-price',       # Sale price, includes discount
            'retail-price',
            'available-from',#15
            'available-to',
            'brand',
            'delivery-price',
            'keywords',             # ~~ delimited
            'manufacturer-part-no',#20
            'manufacturer',
            'shipping-information',
            'availability',
            'universal-product-code',
            'classification-id',#25
            'currency',
            'm1',                   # blank field
            'tracking-pixel-url',#28

            #'miscellaneous-attribute',
            #'color',
            #'gender',
            #'agegroup',
        )

    def start_requests(self):
        meta = {'ftp_user': 'apparelrow', 'ftp_password': 'fdzfdFiJ'}
        for url in self.start_urls:
            yield Request(url, meta=meta, dont_filter=True)

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
        super(MyWardrobeSpider, self).__init__(name, **kwargs)
    """

    def parse_row(self, response, row):
        item = Product()
        key = key_regex1.search(row.get('product-url'))
        if key:
            item['key'] = urllib.unquote(force_bytes(key.group(1)))
            item['key'] = item['key'].split('?', 1)[0]
        item['sku'] = row.get('product-id')
        item['name'] = row.get('product-name')
        item['vendor'] = self.name
        item['url'] = row.get('product-url')
        item['affiliate'] = self.AFFILIATE_LINKSHARE
        item['category'] = '%s > %s' % (row.get('secondary-category'), row.get('category'))
        item['description'] = row.get('description')
        item['brand'] = row.get('manufacturer') or row.get('brand')
        item['gender'] = 'W'
        item['colors'] = row.get('color')
        item['regular_price'] = row.get('retail-price')
        item['discount_price'] = row.get('discount-price')
        item['currency'] = row.get('currency')
        item['in_stock'] = True #Not working anymoreif row.get('availability', '').lower() == 'in stock' else False
        item['stock'] = '-1'
        item['image_urls'] = [row.get('image-url').replace("t_","m1_") if row.get('image-url',None) else '']

        return item