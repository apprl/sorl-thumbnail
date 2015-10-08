from scrapy.contrib.spiders import XMLFeedSpider

from spiderpig.spidercrawl.items import Product, ProductLoader
from spiderpig.spidercrawl.spiders import AffiliateMixin
from scrapy import log
#from spiderpig.spidercrawl.utils import ApprlFileLogObserver,WARNING

class MqSpider(XMLFeedSpider, AffiliateMixin):
    name = 'mq'
    allowed_domains = ['mq.se']
    start_urls = ['http://www.mq.se/xml/mythings/artInfo.xml']
    itertag = 'product'


    """def __init__(self, name=None, **kwargs):
        loglevel = WARNING
        file_to_write = open('%s.log' % self.name,'a')
        logencoding = "utf-8"
        crawler = name
        sflo = ApprlFileLogObserver(file_to_write, loglevel, logencoding, crawler)
        log.log.addObserver(sflo.emit)
        super(MqSpider, self).__init__(name, **kwargs)
    """

    def parse_node(self, response, node):
        in_stock = node.xpath('inStock/text()').extract()[0]

        real_categories = []
        categories = list(node.xpath('Categories/category/text()').extract())
        for category in categories:
            if 'Kategorier' in category and 'Visa Alla' not in category:
                real_categories.append(category)
        if real_categories:
            category = sorted(real_categories, key=len)[-1]
        else:
            category = None

        description = node.xpath('description/text()').extract()[0]
        name = node.xpath('name/text()').extract()[0]

        l = ProductLoader(item=Product(), selector=node)
        l.add_xpath('key', 'link/text()')
        l.add_xpath('sku', '@id')
        l.add_value('name', name)
        l.add_value('vendor', self.name)
        l.add_xpath('url', 'link/text()')
        l.add_value('affiliate', self.AFFILIATE_AAN)
        l.add_value('category', category)
        l.add_value('description', description)
        l.add_xpath('brand', 'brand/text()')
        l.add_xpath('gender', 'Categories/*[1]/text()')
        l.add_value('colors', name + " " + description)
        l.add_xpath('regular_price', 'price/text()')
        l.add_xpath('discount_price', 'new_price/text()')
        l.add_xpath('currency', 'currency/text()')
        l.add_value('in_stock', True if in_stock == 'TRUE' else False)
        l.add_value('stock', '-')
        l.add_xpath('image_urls', 'images/image/@url')

        return l.load_item()
