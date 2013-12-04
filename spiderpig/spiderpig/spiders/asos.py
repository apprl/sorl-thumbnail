import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider

from django.utils.encoding import force_bytes

from spiderpig.items import Product
from spiderpig.spiders import AffiliateMixin


key_regex1 = re.compile(r'\[\[(.+)\]\]')


class AsosSpider(CSVFeedSpider, AffiliateMixin):
    name = 'asos'
    allowed_domains = ['asos.com']
    start_urls = ['http://productdata.zanox.com/exportservice/v1/rest/19595318C106179573.csv?ticket=340591472561713FE451A566542E92402FC9943162D23D40322CFA79DD48C142&columnDelimiter=,&textQualifier=DoubleQuote&nullOutputFormat=NullValue&dateFormat=dd/MM/yyyy%20HH:mm:ss&decimalSeparator=period&gZipCompress=yes&id&pg&nb&na&pp&po&cy&du&df&dt&ds&dl&mc&zi&ia&im&il&mn&lk&cm&td&tm&ea&is&sh&sn&x1&x2&x3']
    delimiter = ','

    def parse_row(self, response, row):
        import pprint
        pprint.pprint(row)

        item = Product()
        key = key_regex1.search(row.get('ZanoxProductLink'))
        if key:
            item['key'] = urllib.unquote(force_bytes(key.group(1)))
        item['key'] = row.get('link')
        item['sku'] = row.get('MerchantProductNumber')
        item['name'] = row.get('ProductName')
        item['vendor'] = self.name
        item['url'] = row.get('ZanoxProductLink')
        item['affiliate'] = self.AFFILIATE_ZANOX
        item['category'] = row.get('MerchantProductCategory')
        item['description'] = row.get('ProductLongDescription')
        item['brand'] = row.get('ProductManufacturerBrand')
        item['gender'] = row.get('MerchantProductCategory')
        item['colors'] = row.get('ExtraTextOne')
        item['regular_price'] = row.get('ProductPriceOld')
        item['discount_price'] = row.get('ProductPrice')
        item['currency'] = row.get('CurrencySymbolOfPrice')
        item['in_stock'] = True
        item['stock'] = ''
        item['image_urls'] = [row.get('ImageLargeURL')]

        if not item['regular_price'] and item['discount_price']:
            item['regular_price'], item['discount_price'] = item['discount_price'], item['regular_price']

        return item
