from scrapy.contrib.spiders import XMLFeedSpider

from spiderpig.spidercrawl.items import Product, ProductLoader
from spiderpig.spidercrawl.spiders import AffiliateMixin, PriceMixin
from scrapy.exceptions import NotConfigured, NotSupported
from scrapy.selector import Selector

from scrapy import log

class WolfnBadger(XMLFeedSpider, AffiliateMixin, PriceMixin):
    name = 'wolfnbadger'
    allowed_domains = ['www.wolfandbadger.com']
    start_urls = ['https://www.wolfandbadger.com/media/feeds/products_excluding_variants_eur.xml']
    namespaces = [('g', 'http://base.google.com/ns/1.0')]
    itertag = 'entry'

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
        super(WolfnBadger, self).__init__(name, **kwargs)
    """
    def parse(self, response):
        if not hasattr(self, 'parse_node'):
            raise NotConfigured('You must define parse_node method in order to scrape this XML feed')
        response = self.adapt_response(response)
        selector = Selector(response, type='xml')
        selector.remove_namespaces()
        nodes = selector.xpath('//%s' % self.itertag)
        return self.parse_nodes(response, nodes)

    def parse_nodes(self, response, nodes):
        from scrapy.utils.spider import iterate_spider_output
        for selector in nodes:
            selector.remove_namespaces()
            ret = iterate_spider_output(self.parse_node(response, selector))
            for result_item in self.process_results(response, ret):
                yield result_item

    def parse_node(self, response, node):
        in_stock = node.xpath('availability/text()').extract()[0]

        currency = ''
        regular_price = node.xpath('price/text()').extract()
        if regular_price:
            regular_price, currency = self.parse_price(regular_price[0])

        l = ProductLoader(item=Product(), selector=node)
        l.add_xpath('key', 'link/text()')
        l.add_xpath('sku', 'id/text()')
        l.add_xpath('name', 'title/text()')
        l.add_value('vendor', self.name)
        l.add_xpath('url', 'link/text()')
        l.add_value('affiliate', self.AFFILIATE_AAN)
        l.add_xpath('category', 'google_product_category/text()')
        l.add_xpath('description', 'description/text()')
        l.add_xpath('brand', 'brand/text()')
        l.add_xpath('gender', 'gender/text()')
        l.add_xpath('colors', 'color/text()')
        l.add_value('regular_price', regular_price)
        l.add_value('discount_price', regular_price)
        l.add_value('currency', 'EUR')
        l.add_value('in_stock', True if in_stock == 'in stock' else False)
        l.add_xpath('stock', 'quantity/text()')
        #if image:
        l.add_xpath('image_urls', 'image_link/text()')
        #else:
        #    l.add_value('currency', 'GBP')

        return l.load_item()
