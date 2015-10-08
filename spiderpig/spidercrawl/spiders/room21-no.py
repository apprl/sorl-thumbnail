from scrapy.contrib.spiders import XMLFeedSpider

from spiderpig.spidercrawl.items import Product, ProductLoader
from spiderpig.spidercrawl.spiders import AffiliateMixin, PriceMixin, KeyExtractorMixin

class Room21NOSpider(XMLFeedSpider, AffiliateMixin, PriceMixin, KeyExtractorMixin):
    name = 'room21-no'
    allowed_domains = ['room21.no']
    start_urls = ['http://www.room21.no/agent/Google_NO_products_gs7sa.xml']
    namespaces = [('g', 'http://base.google.com/ns/1.0')]
    itertag = 'item'

    def parse_node(self, response, node):
        if node.xpath('g:id/text()').extract():
            in_stock = node.xpath('g:availability/text()').extract()[0]
            currency = ''
            regular_price = node.xpath('g:price/text()').extract()
            if regular_price:
                regular_price, currency = self.parse_price(regular_price[0])

            discount_price = node.xpath('g:sale_price/text()').extract()
            if discount_price:
                discount_price, _ = self.parse_price(discount_price[0])
            else:
                discount_price = ''

            google_category = node.xpath('g:google_product_category/text()').extract()
            google_category = google_category[0] if google_category else ''

            product_type_array = node.xpath('g:product_type/text()').extract()
            product_type = product_type_array[1] if len(product_type_array) > 1 else product_type_array[0]
            product_type = ' > '.join(product_type.split(" > ")[-2:])

            description = node.xpath('description/text()').extract()[0]
            name = node.xpath('title/text()').extract()[0]

            category = ''
            if google_category or product_type:
                category = ' > '.join([x for x in [google_category, product_type] if x])

            l = ProductLoader(item=Product(), selector=node)
            l.add_xpath('key', 'link/text()')
            l.add_xpath('sku', 'g:id/text()')
            l.add_value('name', name)
            l.add_value('vendor', self.name)
            l.add_xpath('url', 'link/text()')
            l.add_value('affiliate', self.AFFILIATE_AAN)
            l.add_value('description', description)
            l.add_xpath('brand', 'g:brand/text()')
            l.add_value('colors', name + ' ' + description)
            l.add_value('regular_price', regular_price)
            l.add_value('discount_price', discount_price if discount_price else regular_price)
            l.add_value('currency', currency)
            l.add_value('in_stock', True if in_stock == 'in stock' else False)
            l.add_value('stock', '-')
            l.add_xpath('image_urls', 'g:image_link/text()')
            l.add_value('category', category)
            l.add_value('gender', 'U')

            return l.load_item()