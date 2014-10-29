from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


class BelstaffSpider(CSVFeedSpider, AffiliateMixin):
    name = 'belstaff'
    allowed_domains = ['belstaff.com']
    start_urls = ['http://customfeeds.easyfeed.goldenfeeds.com/1763/custom-feed-linkshare-belstaf311-belstaff-uk.csv.zip']
    delimiter = ','

    def parse_row(self, response, row):
        item = Product()
        item['name'] = row.get('product_name')
        item['vendor'] = self.name
        item['url'] = row.get('original_url')
        item['key'] = row.get('original_url').split('?')[0]
        item['sku'] = row.get('product_number')
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('category')
        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = row.get('gender')
        item['colors'] = row.get('colors')
        item['regular_price'] = row.get('price')
        item['discount_price'] = row.get('price')
        item['currency'] = row.get('currency')
        item['in_stock'] = True if row.get('availability') == 'in stock' else False
        item['stock'] = '-'
        item['image_urls'] = [row.get('large_image_URL')]

        return item