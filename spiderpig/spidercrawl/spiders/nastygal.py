import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider

from django.utils.encoding import force_bytes

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin

#from spiderpig.spidercrawl.utils import ApprlFileLogObserver,WARNING
#from scrapy import log

key_regex1 = re.compile(r'\?url=(.+)$')


class NastyGalSpider(CSVFeedSpider, AffiliateMixin):
    name = 'nastygal'
    allowed_domains = ['nastygal.com']
    start_urls = ['http://datatransfer.cj.com/datatransfer/files/3131851/outgoing/productcatalog/156759/NastyGal_com-Nasty_Gal.txt.gz']
    delimiter = ','
    http_user = '3131851'
    http_pass = 'f3NPxFso'

    """def __init__(self, name=None, **kwargs):g
        loglevel = WARNING
        file_to_write = open('%s.log' % self.name,'a')
        logencoding = "utf-8"
        crawler = name
        sflo = ApprlFileLogObserver(file_to_write, loglevel, logencoding, crawler)
        log.log.addObserver(sflo.emit)
        super(NastyGalSpider, self).__init__(name, **kwargs)
    """

    def parse_row(self, response, row):
        item = Product()
        key = key_regex1.search(row.get('BUYURL'))

        if key:
            shortened_url = urllib.unquote(force_bytes(key.group(1))).split("?")[0]
            item['key'] = shortened_url
        item['sku'] = row.get('SKU')
        item['name'] = row.get('NAME')
        item['vendor'] = self.name
        item['url'] = row.get('BUYURL')
        item['affiliate'] = self.AFFILIATE_CJ
        item['category'] = row.get('ADVERTISERCATEGORY')
        item['description'] = row.get('DESCRIPTION')
        item['brand'] = row.get('MANUFACTURER')
        item['gender'] = 'W'
        item['colors'] = row.get('KEYWORDS')
        item['regular_price'] = row.get('SALEPRICE')
        item['discount_price'] = row.get('PRICE')
        item['currency'] = row.get('CURRENCY')
        item['in_stock'] = True if row.get('INSTOCK') == 'yes' else False
        item['stock'] = ''
        item['image_urls'] = [row.get('IMAGEURL', '')]

        return item
