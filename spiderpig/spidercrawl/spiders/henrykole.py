from scrapy.contrib.spiders import XMLFeedSpider

from spiderpig.spidercrawl.items import Product, ProductLoader
from spiderpig.spidercrawl.spiders import AffiliateMixin

import HTMLParser


class HenryKoleSpider(XMLFeedSpider, AffiliateMixin):
    name = 'henrykole'
    allowed_domains = ['henrykole.com', 'henrykole.se']
    start_urls = ['http://www.henrykole.se/feeds/APPRL.xml']
    itertag = 'product'

    def parse_node(self, response, node):
        parser = HTMLParser.HTMLParser()
        description_raw = node.xpath('description/text()').extract()
        description = parser.unescape(description_raw)
        l = ProductLoader(item=Product(), selector=node)
        l.add_xpath('key', 'link/text()')
        l.add_xpath('sku', 'id/text()')
        l.add_xpath('name', 'title/text()')
        l.add_value('vendor', self.name)
        l.add_xpath('url', 'link/text()')
        l.add_value('affiliate', self.AFFILIATE_AAN)
        l.add_xpath('category', 'category/text()')
        l.add_value('description', description)
        l.add_xpath('brand', 'brand /text()')
        l.add_xpath('colors', 'variations/variation/color/text()')
        l.add_value('gender', 'W')
        l.add_xpath('regular_price', 'old_price/text()')
        l.add_xpath('discount_price', 'price/text()')
        l.add_value('currency', 'SEK')
        l.add_value('in_stock', True)
        l.add_value('stock', '-')
        l.add_xpath('image_urls', 'photos/images/url/text()')

        return l.load_item()
