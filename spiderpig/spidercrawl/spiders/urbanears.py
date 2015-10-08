from scrapy.contrib.spiders import CSVFeedSpider
from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


class UrbanearsSpider(CSVFeedSpider, AffiliateMixin):
    name = 'urbanears'
    allowed_domains = ['urbanears.com']
    start_urls = ['http://www1.urbanears.com/feeds/generic_urban_sweden.csv']
    delimiter = ';'

    def parse_row(self, response, row):
        in_stock = row.get('Is in stock')
        stock = 0
        if in_stock == 'in stock':
            stock = 1

        item = Product()

        item['key'] = row.get('URL ')
        item['sku'] = row.get('SKU')
        item['name'] = row.get('Name')
        item['vendor'] = self.name
        item['url'] = row.get('URL ')
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('Manufacturer')
        item['description'] = row.get('description')
        item['brand'] = row.get('Manufacturer')
        item['gender'] = 'U'
        item['colors'] = row.get('Name')
        item['regular_price'] = row.get('Price')
        item['discount_price'] = row.get('Price')
        item['currency'] = 'SEK'
        item['in_stock'] = True if stock > 0 else False
        item['stock'] = stock
        item['image_urls'] = [row.get('Image'),]

        return item
