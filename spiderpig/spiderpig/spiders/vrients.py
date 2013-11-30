from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.spiders import CSVFeedSpider
from scrapy.http import Request

from spiderpig.items import Product, ProductLoader


class VrientsSpider(CSVFeedSpider):
    name = 'vrients'
    allowed_domains = ['vrients.com']
    start_urls = ['http://www.vrients.com/media/feed/apprl.csv']
    delimiter = ','
    #headers = ['id', 'name', 'description']

    def parse_row(self, response, row):
        print row

        item = Product()
        # TODO: remove ?source=apprl, keep it for url
        item['key'] = row.get('link')
        if item['key']:
            item['key'] = item['key'].replace('?source=apprl', '')
        item['name'] = row.get('title')
        item['vendor'] = VrientsSpider.name
        item['url'] = row.get('link')

        item['description'] = row.get('description')
        item['brand'] = row.get('brand')
        item['gender'] = 'M'
        item['regular_price'] = row.get('price')
        item['discount_price'] = row.get('sale_price')
        item['currency'] = 'EUR'
        

        # Replace the return item statement with this to fetch and parse the product page
        #return [item, Request(item['key'], callback=self.parse_item)]
        return item

    #def parse_item(self, response):
        #yield None


#class FifthAvenueSpider(XMLFeedSpider):
    #name = 'fifth_avenue'
    #allowed_domains = ['vave-shoerepair.com']
    #start_urls = [
        #'http://www.vave-shoerepair.com/en/search/bysearchdefinition/shop-socially?partial=shopsocially&viewall',
    #]
    #iterator = 'iternodes'
    #itertag = 'product'

    #def parse_item(self, response):
        #hxs = HtmlXPathSelector(response)
        #price =  hxs.select('//p[contains(concat(" ", normalize-space(@class), " "), " price ")]')

        #regular_price = price.select('//strike/text()').extract()
        #discount_price = price.select('span[contains(@class, "pricevalue")]/text()').extract()
        #if not regular_price:
            #regular_price = price.select('span[contains(@class, "pricevalue")]/text()').extract()
            #discount_price = None

        #l = ProductLoader(item=Product(), selector=hxs)
        #l.add_xpath('name', '//h1/text()')
        #l.add_xpath('colors', '//h3[text()="Color"]/following::div[1]/text()')

        #l.add_value('brand', 'Fifth Avenue Shoe Repair')
        #l.add_value('key', response.url)
        #l.add_value('url', response.url)
        #l.add_value('vendor', FifthAvenueSpider.name)
        #l.add_value('regular_price', regular_price)
        #l.add_value('discount_price', discount_price)

        #yield l.load_item()

    #def parse_node(self, response, node):
        #l = ProductLoader(item=Product(), selector=node)
        #l.add_xpath('name', '//product-name/text()')
        #l.add_xpath('brand', '//manufacturer/text()')
        #l.add_xpath('description', '//description/text()')
        #l.add_xpath('category', '//category/text()')
        #l.add_xpath('gender', '//gender/text()')
        #l.add_xpath('currency', '//currency/text()')
        #l.add_xpath('url', '//product-url/text()')
        #l.add_xpath('image_urls', '//image-url/text()')
        #l.add_xpath('key', '//product-url/text()')
        #l.add_xpath('buy_url', '//product-url/text()')

        ## TODO: discount_price, in_stock, colors, affiliate (buy url without affiliate right now)
        ## TODO: fetch url and scrape for more information

        #l.add_value('affiliate', '')
        #l.add_value('vendor', FifthAvenueSpider.name)
        #l.add_value('in_stock', 'in-stock')

        #item = l.load_item()
        #item['in_stock'] = bool(item.get('in_stock'))

        #return [item, Request(item['url'], callback=self.parse_item)]
