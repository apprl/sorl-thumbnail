import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider

from django.utils.encoding import force_bytes

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


key_regex1 = re.compile(r'\[\[(.+)\]\]')


class DagmarSpider(CSVFeedSpider, AffiliateMixin):
    name = 'dagmar'
    allowed_domains = ['houseofdagmar.se']
    start_urls = ['http://productdata.zanox.com/exportservice/v1/rest/30634622C39021886.csv?ticket=D2392FA58B5C2F1C99BB03D9CA0C3959&columnDelimiter=,&textQualifier=DoubleQuote&nullOutputFormat=NullValue&dateFormat=dd/MM/yyyy HH:mm:ss&decimalSeparator=period&gZipCompress=null&id&pg&nb&na&pp&po&cy&du&df&dt&ds&dl&mc&zi&ia&im&il&mn&lk&cm&td&tm&ea&is&sh&sn&x1&x2&x3']
    delimiter = ','

    def parse_row(self, response, row):
        item = Product()
        key = key_regex1.search(row.get('ZanoxProductLink'))
        if key:
            item['key'] = 'http://www.houseofdagmar.se/%s' % (urllib.unquote(force_bytes(key.group(1))),)
        item['sku'] = row.get('MerchantProductNumber')
        item['name'] = row.get('ProductName')
        item['vendor'] = self.name
        item['url'] = row.get('ZanoxProductLink')
        item['affiliate'] = self.AFFILIATE_ZANOX
        item['category'] = row.get('MerchantProductCategory')
        item['description'] = row.get('ProductShortDescription')
        item['brand'] = row.get('ProductManufacturerBrand') if row.get('ProductManufacturerBrand') else 'Dagmar'
        item['gender'] = 'W'
        item['colors'] = row.get('ProductName') + row.get('ProductShortDescription')
        item['regular_price'] = row.get('ProductPrice')
        item['discount_price'] = row.get('ProductPrice')
        item['currency'] = row.get('CurrencySymbolOfPrice')
        item['in_stock'] = True
        item['stock'] = '-'
        item['image_urls'] = [row.get('ImageLargeURL')]

        return item
