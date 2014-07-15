from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import TakeFirst, Identity, MapCompose
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from spiderpig.items import Product

class ProductLoader(XPathItemLoader):
    default_output_processor = TakeFirst()
    default_input_processor = MapCompose(unicode.strip)

    images_out = Identity()


class SunpocketSpider(CrawlSpider):
    name = 'vrients'
    allowed_domains = ['vrients.com']
    start_urls = [
        #'http://www.vrients.com/en/'
        'http://www.vrients.com/en/sales.html'
    ]
    rules = [Rule(SgmlLinkExtractor(allow=['/en/sales/.+\.html']), 'parse_product')]

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response).select('//div[contains(@class, "product-view")]')
        if not hxs:
            return

        l = ProductLoader(item=Product(), selector=hxs)
        l.add_xpath('name', '//div[contains(@class, "product-subname")]/text()')
        l.add_xpath('brand', '//h1/text()')
        l.add_xpath('description', '//div[contains(@id, "description")]/text()')
        #l.add_xpath('price', '//span[contains(@class, "price")]/text()')
        #l.add_xpath('in_stock', '//span[contains(@class, "sold")]/text()')
        #l.add_xpath('images', '//ul[contains(@class, "img360")]/li/a/img/@src')
        #l.add_value('url', response.url)
        #l.add_value('category', 'unisex sunglasses')

        regular_price = map(unicode.strip, hxs.select('//span[contains(@class, "regular-price")]/span/text()').extract())
        original_price = map(unicode.strip, hxs.select('//p[contains(@class, "old-price")]/span/text()').extract())
        discount_price = map(unicode.strip, hxs.select('//p[contains(@class, "special-price")]/span/text()').extract())

        print regular_price, original_price, discount_price

        base_url = get_base_url(response)

        item = l.load_item()
        #item['in_stock'] = not bool(item.get('in_stock'))
        #item['price'] = item.get('price', '').replace(u'\xa0', u' ')
        #item['images'] = [
            #urljoin_rfc(base_url,
                        #image.replace('s360', 'big'))
            #for image in item.get('images', [])
        #]

        return item
