import re
import urllib

from scrapy.contrib.spiders import CSVFeedSpider

from django.utils.encoding import force_bytes

from spiderpig.items import Product
from spiderpig.spiders import AffiliateMixin


key_regex1 = re.compile(r'\[\[(.+)\]\]')


class MyWardrobeSpider(CSVFeedSpider, AffiliateMixin):
    name = 'my-wardrobe'
    allowed_domains = ['my-wardrobe.com']
    start_urls = ['http://productdata.zanox.com/exportservice/v1/rest/22618414C74707054.csv?ticket=D2392FA58B5C2F1C99BB03D9CA0C3959&columnDelimiter=;&textQualifier=none&nullOutputFormat=NullValue&dateFormat=dd/MM/yyyy%20HH:mm:ss&decimalSeparator=comma&id=&na=&pp=&mc=&mn=&lk=&td=&ea=&pg=&nb=&po=&cy=&du=&df=&dt=&ds=&dl=&zi=&ia=&im=&il=&cm=&tm=&is=&sh=&sn=&x1=&x2=&x3=&gZipCompress=yes']
    delimiter = ';'

    def parse_row(self, response, row):
        item = Product()
        key = key_regex1.search(row.get('ZanoxProductLink'))
        if key:
            key = urllib.unquote(force_bytes(key.group(1)))
            key = key.split('?', 1)[0]
            item['key'] = 'http://www.my-wardrobe.com%s' % (key,)
        item['sku'] = row.get('MerchantProductNumber')
        item['name'] = row.get('ProductName')
        item['vendor'] = self.name
        item['url'] = row.get('ZanoxProductLink')
        item['affiliate'] = self.AFFILIATE_ZANOX
        item['category'] = '%s > %s' % (row.get('ExtraTextOne'), row.get('MerchantProductCategory'))
        item['description'] = row.get('ProductLongDescription')
        item['brand'] = row.get('ProductManufacturerBrand')
        item['gender'] = row.get('ExtraTextOne')
        item['colors'] = row.get('ExtraTextThree')
        item['regular_price'] = row.get('ProductPriceOld', '').replace(',', '.')
        item['discount_price'] = row.get('ProductPrice', '').replace(',', '.')
        item['currency'] = row.get('CurrencySymbolOfPrice')
        item['in_stock'] = True
        item['stock'] = ''
        item['image_urls'] = [row.get('ImageLargeURL')]

        if not item['regular_price'] and item['discount_price']:
            item['regular_price'], item['discount_price'] = item['discount_price'], item['regular_price']

        return item
