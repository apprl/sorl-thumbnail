from scrapy.contrib.spiders import XMLFeedSpider

from spiderpig.items import Product, ProductLoader
from spiderpig.spiders import AffiliateMixin, PriceMixin


class OddMollySpider(XMLFeedSpider, AffiliateMixin, PriceMixin):
    name = 'jc'
    allowed_domains = ['jc.se']
    start_urls = ['https://rnb-production.vaimo.com/feeds/GoogleShopping_JC.xml']
    namespaces = [('g', 'http://base.google.com/ns/1.0')]
    itertag = 'item'

    def parse_node(self, response, node):
        in_stock = node.xpath('g:availability/text()').extract()[0]
        if in_stock:
            in_stock = in_stock.strip()

        regular_price = node.xpath('g:price/text()').extract()
        if regular_price:
            regular_price, currency = self.parse_price(regular_price[0])

        if not currency:
            currency = 'SEK'

        discount_price = node.xpath('g:sale_price/text()').extract()
        if discount_price:
            discount_price, _ = self.parse_price(discount_price[0])
        else:
            discount_price = ''

        # Select image ending with _90 if it exists
        images = node.xpath('g:image_link/text()').extract()
        extra_images = node.xpath('g:additional_image_link/text()').extract()
        for image in extra_images:
            if '_90' in image:
                images = [image]
                break

        l = ProductLoader(item=Product(), selector=node)
        l.add_xpath('key', 'link/text()')
        l.add_xpath('sku', 'g:id/text()')
        l.add_xpath('name', 'title/text()')
        l.add_value('vendor', self.name)
        l.add_xpath('url', 'link/text()')
        l.add_value('affiliate', self.AFFILIATE_AAN)
        l.add_xpath('category', 'g:product_type/text()')
        l.add_xpath('description', 'description/text()')
        l.add_xpath('brand', 'g:brand/text()')
        l.add_xpath('gender', 'g:product_type/text()')
        l.add_xpath('colors', 'g:color/text()')
        l.add_value('regular_price', regular_price)
        l.add_value('discount_price', discount_price)
        l.add_value('currency', currency)
        l.add_value('in_stock', True if in_stock == 'in stock' else False)
        l.add_value('stock', '')
        l.add_value('image_urls', images)

        return l.load_item()
