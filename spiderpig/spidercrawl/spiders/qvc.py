import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider

from django.utils.encoding import force_bytes

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


key_regex1 = re.compile(r'\?url=(.+)$')

class QVCSpider(CSVFeedSpider, AffiliateMixin):
    name = 'qvc'
    allowed_domains = ['qvc.com']
    start_urls = ['http://datatransfer.cj.com/datatransfer/files/3131851/outgoing/productcatalog/162088/QVC_com-QVC_Product_Catalog_Project_Runaway_All_Stars_Feed.txt.gz']
    delimiter = ','
    http_user = '3131851'
    http_pass = 'f3NPxFso'

    def parse_row(self, response, row):
        item = Product()
        key = key_regex1.search(row.get('BUYURL'))
        if key:
            item['key'] = urllib.unquote(force_bytes(key.group(1)))
        item['sku'] = row.get('SKU')
        item['name'] = row.get('NAME')
        item['vendor'] = self.name
        item['url'] = row.get('BUYURL')
        item['affiliate'] = self.AFFILIATE_CJ
        item['category'] = row.get('ADVERTISERCATEGORY')
        item['description'] = row.get('DESCRIPTION')
        item['brand'] = row.get('MANUFACTURER')
        item['gender'] = 'U' if row.get('THIRDPARTYCATEGORY') == '' else row.get('THIRDPARTYCATEGORY')
        item['colors'] = row.get('NAME') + row.get('DESCRIPTION')
        item['regular_price'] = row.get('SALEPRICE')
        item['discount_price'] = row.get('PRICE')
        item['currency'] = row.get('CURRENCY')
        item['in_stock'] = True if row.get('INSTOCK') == 'yes' else False
        item['stock'] = '-'
        item['image_urls'] = [row.get('IMAGEURL', '')]