from scrapy.contrib.spiders import XMLFeedSpider

from spiderpig.spidercrawl.items import Product, ProductLoader
from spiderpig.spidercrawl.spiders import AffiliateMixin


class ElevenfiftynineSpider(XMLFeedSpider, AffiliateMixin):
    name = 'elevenfiftynine'
    allowed_domains = ['elevenfiftynine.se']
    start_urls = ['http://elevenfiftynine.se/xml_feeds.php?id=3']
    itertag = 'product'

    def parse_node(self, response, node):
        in_stock = node.xpath('active/text()').extract()[0]

        description = node.xpath('descriptions/descriptions-en/description-en/text()').extract()[0]
        if not description:
            description = node.xpath('descriptions/descriptions-sv/description-sv/text()').extract()[0]

        l = ProductLoader(item=Product(), selector=node)
        l.add_xpath('key', 'product_url/text()')
        l.add_xpath('sku', 'supplier_reference/text()')
        l.add_xpath('name', 'descriptions/descriptions-en/name-en/text()')
        l.add_value('vendor', self.name)
        l.add_xpath('url', 'product_url/text()')
        l.add_value('affiliate', self.AFFILIATE_AAN)
        l.add_xpath('category', 'default_category/category_default_name-en/text()')
        l.add_value('description', description)
        l.add_xpath('brand', 'manufacturer_name/text()')
        l.add_value('gender', 'U')
        l.add_xpath('colors', 'descriptions/descriptions-en/name-en/text()')
        l.add_xpath('regular_price', 'price_sale/text()')
        l.add_xpath('discount_price', 'price_sale/text()')
        l.add_value('currency', 'SEK')
        l.add_value('in_stock', True if in_stock == '1' else False)
        l.add_value('stock', '-')
        l.add_xpath('image_urls', 'images/thickbox/text()')

        return l.load_item()
