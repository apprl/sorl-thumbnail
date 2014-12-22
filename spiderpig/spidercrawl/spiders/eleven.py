# -*- coding: utf-8 -*-
from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spidercrawl.items import Product
from spiderpig.spidercrawl.spiders import AffiliateMixin


class ElevenSpider(CSVFeedSpider, AffiliateMixin):
    name = 'eleven'
    allowed_domains = ['eleven.se']
    start_urls = ['http://eleven.se/pricefile/83bc8b0028c7fb7c0c7fa1135d0d71ccb338a3d9/']
    delimiter = ';'
    headers = (
    u'Produktnummer',
    u'Tillverkarens prod.nr./SKU',
    u'Streckkod',
    u'Produkttitel',
    u'Pris (inkl. moms)',
    u'Fraktkostnad (inkl. moms)',
    u'Lager',
    u'Grupp',
    u'Märke/Tillverkare',
    u'Länk',
    u'Länk - Bild',
    u'Beskrivning',
    u'MAN, WOMAN, UNISEX',
    u'Ordinarie Pris'
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
        super(ElevenSpider, self).__init__(name, **kwargs)
    """

    def parse_row(self, response, row):
        item = Product()
        item['key'] = row.get(u'Länk')
        item['sku'] = row.get('Tillverkarens prod.nr./SKU') if row.get('Tillverkarens prod.nr./SKU',None) else row.get('Produktnummer')
        item['name'] = row.get('Produkttitel')
        item['vendor'] = self.name
        item['url'] = row.get(u'Länk') + "?utm_source=apprl&utm_medium=affiliate&utm_campaign=apprl"
        item['affiliate'] = self.AFFILIATE_AAN
        item['category'] = "%s -> %s" % (row.get(u'MAN, WOMAN, UNISEX'),row.get('Grupp') )
        item['description'] = row.get('Beskrivning')
        item['brand'] = row.get(u'Märke/Tillverkare')
        item['gender'] = row.get(u'MAN, WOMAN, UNISEX')
        item['colors'] = ''

        regular_price = row.get('Ordinarie Pris')
        discount_price = row.get('Pris (inkl. moms)')

        item['regular_price'] = regular_price if regular_price else discount_price
        item['discount_price'] = discount_price

        item['currency'] = 'SEK'
        item['in_stock'] = True
        item['stock'] = '-'
        item['image_urls'] = [row.get(u'Länk - Bild')]

        return item
