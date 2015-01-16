# -*- coding: utf-8 -*-
from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


class LaurenBSpider(CSVFeedSpider, AffiliateMixin):
    name = 'laurenb'
    #allowed_domains = ['bjornborg.se']
    start_urls = ['https://www.laurenbbeauty.com/products.txt']
    delimiter = '\t'

    headers = (
  'Product ID',
  'Product URL',
  'Image URL',
  'Product Name',
  'Product Text Description',
  'Product Category',
  'Brand Name',
  'Price',
    )


    def parse_row(self, response, row):
        item = Product()
        item['name'] = row.get('Product Name')
        item['key'] = row.get('Product URL')
        item['url'] = row.get('Product URL')
        item['sku'] = row.get('Product ID')
        item['vendor'] = self.name
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('Product Category')
        item['description'] = row.get('Product Text Description')
        item['brand'] = row.get('Brand Name')
        item['gender'] = row.get('Product Category')
        item['colors'] = row.get('Product Text Description')
        item['regular_price'] = row.get('Price')
        item['discount_price'] = row.get('Price')
        item['currency'] = 'USD'
        item['in_stock'] = True
        item['stock'] = '-'
        item['image_urls'] = [row.get('Image URL')]
        return item
