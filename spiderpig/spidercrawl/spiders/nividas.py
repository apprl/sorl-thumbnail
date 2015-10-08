from spiderpig.spidercrawl.items import Product, ProductLoader
from spiderpig.spidercrawl.spiders import AffiliateMixin, PriceMixin
from scrapy.contrib.spiders import XMLFeedSpider

class NividasSpider(XMLFeedSpider, AffiliateMixin, PriceMixin):
    name = 'nividas'
    allowed_domains = ['nividas.com']
    start_urls = ['http://nividas.com/index.php/amfeed/main/download/file/pf_apprl.xml/']
    itertag = 'product'

    def parse_node(self, response, node):
        description = node.xpath('product-text-description/text()').extract()[0]
        name = node.xpath('product-name/text()').extract()[0]

        l = ProductLoader(item=Product(), selector=node)
        l.add_xpath('key', 'product-url/text()')
        l.add_xpath('sku', 'product-id/text()')
        l.add_value('name', name)
        l.add_value('vendor', self.name)
        l.add_xpath('url', 'product-url/text()')
        l.add_value('affiliate', self.AFFILIATE_AAN)
        l.add_xpath('category', 'product-category/text()')
        l.add_value('description', description)
        l.add_xpath('brand', 'brand-name/text()')
        l.add_xpath('gender', 'gender/text()')
        l.add_value('colors', name + " " + description)
        l.add_xpath('regular_price', 'price/text()')
        l.add_xpath('discount_price', 'price/text()')
        l.add_value('currency', 'SEK')
        l.add_value('in_stock', True)
        l.add_value('stock', '-')
        l.add_xpath('image_urls', 'image-url/text()')

        return l.load_item()
