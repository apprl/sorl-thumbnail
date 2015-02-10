import re

from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


class AltewaiSaomeSpider(CSVFeedSpider, AffiliateMixin):
    name = 'altewaisaome'
    allowed_domains = ['altewaisaome.com', 'shop.altewaisaome.com']
    start_urls = ['http://merchworld.eu/apprl/get/altewaisaome']
    delimiter = ','
    headers = (
        'productid',
        'productname',
        'category',
        'brand',
        'price',
        'saleprice',   # Sale price, includes discount
        'currency',
        'producturl',
        'imageurl',
        'description',
        'instock',
        'amountinstock',
    )

    def parse_row(self, response, row):
        item = Product()
        item['key'] = row.get('producturl')
        item['sku'] = row.get('productid')
        item['name'] = row.get('productname')
        item['vendor'] = self.name
        item['url'] = row.get('producturl')
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('category')
        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = 'W'
        item['colors'] = row.get('color')
        item['regular_price'] = row.get('price')
        item['discount_price'] = row.get('saleprice')
        item['currency'] = row.get('currency')
        item['in_stock'] = True if row.get('instock').lower() == 'yes' else False
        item['stock'] = row.get('amountinstock')
        item['image_urls'] = [row.get('imageurl')]

        return item
