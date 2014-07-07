# -*- coding: utf-8 -*-
from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


class BjornBorgSpider(CSVFeedSpider, AffiliateMixin):
    name = 'bjornborg'
    #allowed_domains = ['bjornborg.se']
    start_urls = ['http://www.bjornborg.com/media/feeds/apprl/apprl_en.csv']
    delimiter = ';'

    headers = (
        u'name',
        u'desc',
        u'price',
        u'msrp',
        u'currency',
        u'sizes',
        u'category',
        u'images_url',
        u'gender',
        u'brand',
        u'product_url',
        u'ean',
        u'internal_id',
        u'fabric',
        u'color',
    )

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
        super(BjornBorgSpider, self).__init__(name, **kwargs)
    """

    def parse_row(self, response, row):
        item = Product()
        name = row.get("name")
        if name and len(name.split(":")) == 3:
            item['name'] = name.split(":")[0].strip()
        else:
            item['name'] = name.strip()
        item['key'] = row.get(u'product_url').split("?")[0]
        item['url'] = row.get(u'product_url')
        item['sku'] = row.get(u'ean') if row.get(u'ean') else row.get(u'internal_id')
        item['vendor'] = self.name
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = row.get('category')
        item['description'] = row.get('desc')
        item['brand'] = row.get(u'brand')
        item['gender'] = row.get(u'gender')
        item['colors'] = row.get('color')
        item['regular_price'] = row.get('price')
        item['discount_price'] = row.get('msrp')
        item['currency'] = row.get('currency')
        item['in_stock'] = True
        item['stock'] = '-'
        item['image_urls'] = [row.get(u'images_url')]
        return item
