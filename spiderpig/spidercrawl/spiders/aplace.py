from scrapy.contrib.spiders import XMLFeedSpider

from spiderpig.spidercrawl.items import Product, ProductLoader
from spiderpig.spidercrawl.spiders import AffiliateMixin, PriceMixin, KeyExtractorMixin

class AplaceSpider(XMLFeedSpider, AffiliateMixin, PriceMixin, KeyExtractorMixin):
    name = 'aplace'
    allowed_domains = ['aplace.com']
    start_urls = ['http://www.aplace.com/plugin-export/product-feed/se/']
    namespaces = [('g', 'http://base.google.com/ns/1.0')]
    itertag = 'item'

    def parse_node(self, response, node):
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

        key = node.xpath('link/text()').extract()[0]
        google_category = node.xpath('g:google_product_category/text()').extract()
        google_category = google_category[0] if google_category else ''
        product_type = node.xpath('g:product_type/text()').extract()
        product_type = product_type[0] if product_type else ''

        category = ' > '.join([x for x in [google_category, product_type] if x])

        l = ProductLoader(item=Product(), selector=node)
        l.add_value('key', self.get_url_last(key))
        l.add_xpath('sku', 'g:id/text()')
        l.add_xpath('name', 'title/text()')
        l.add_value('vendor', self.name)
        l.add_xpath('url', 'link/text()')
        l.add_value('affiliate', self.AFFILIATE_AAN)
        l.add_value('category', category)
        l.add_xpath('description', 'description/text()')
        l.add_xpath('brand', 'g:brand/text()')
        l.add_xpath('gender', 'g:gender/text()')
        l.add_xpath('colors', 'g:material/text()')
        l.add_value('regular_price', regular_price)
        l.add_value('discount_price', discount_price if discount_price else regular_price)
        l.add_value('currency', currency)
        l.add_value('in_stock', True if in_stock == 'in stock' else False)
        l.add_value('stock', '-')
        l.add_xpath('image_urls', 'g:image_link/text()')

        return l.load_item()