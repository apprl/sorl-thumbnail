from spiderpig.spidercrawl.items import Product, ProductLoader
from spiderpig.spidercrawl.spiders import AffiliateMixin, PriceMixin, KeyExtractorMixin
from scrapy.contrib.spiders import XMLFeedSpider

class ShirtonomySpider(XMLFeedSpider, AffiliateMixin, PriceMixin):
    name = 'shirtonomy'
    allowed_domains = ['shirtonomy.se']
    start_urls = ['https://shirtonomy.se/services/export/']
    itertag = 'item'

    def parse_node(self, response, node):
        in_stock = node.xpath('in_stock/text()').extract()[0]
        image = node.xpath('image_urls/text()').extract()
        l = ProductLoader(item=Product(), selector=node)
        l.add_xpath('key', 'link/text()')
        l.add_xpath('sku', 'sku/text()')
        l.add_xpath('name', 'name/text()')
        l.add_value('vendor', self.name)
        l.add_xpath('url', 'link/text()')
        l.add_value('affiliate', self.AFFILIATE_AAN)
        l.add_xpath('category', 'category/text()')
        l.add_xpath('description', 'description/text()')
        l.add_xpath('brand', 'brand/text()')
        l.add_xpath('gender', 'gender/text()')
        l.add_xpath('colors', 'colors/text()')
        l.add_xpath('regular_price', 'regular_price/text()')
        l.add_xpath('discount_price', 'discount_price/text()')
        l.add_xpath('currency', 'currency/text()')
        l.add_value('in_stock', True if in_stock == 'True' else False)
        l.add_value('stock', '50')
        l.add_value('image_urls', image)

        return l.load_item()
