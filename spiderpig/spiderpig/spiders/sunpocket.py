from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import TakeFirst, Identity
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from spiderpig.items import Product
from spiderpig.utils import generate_buy_url


class ProductLoader(XPathItemLoader):
    default_output_processor = TakeFirst()

    image_urls_out = Identity()


class SunpocketSpider(CrawlSpider):
    name = 'sunpocket'
    allowed_domains = ['sunpocketoriginal.com']
    start_urls = [
        'http://www.sunpocketoriginal.com/',
    ]
    rules = [Rule(SgmlLinkExtractor(allow=['/webstore/.+']), 'parse_product')]

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response).select('//div[contains(@id, "product")]')
        l = ProductLoader(item=Product(), selector=hxs)
        l.add_xpath('name', '//h1/text()')
        l.add_xpath('description', '//article/p[1]/text()')
        l.add_xpath('price', '//span[contains(@class, "price")]/text()')
        l.add_xpath('in_stock', '//span[contains(@class, "sold")]/text()')
        l.add_xpath('image_urls', '//ul[contains(@class, "img360")]/li/a/img/@src')
        l.add_value('url', response.url)
        l.add_value('category', 'unisex sunglasses')
        l.add_value('identifier', response.url.split('/')[-1])
        l.add_value('affiliate', 'cj')
        l.add_value('vendor', SunpocketSpider.name)
        l.add_value('buy_url', generate_buy_url(SunpocketSpider.name, response.url))

        base_url = get_base_url(response)

        item = l.load_item()
        item['in_stock'] = not bool(item.get('in_stock'))
        item['price'] = item.get('price', '').replace(u'\xa0', u' ')
        item['image_urls'] = [
            urljoin_rfc(base_url,
                        image.replace('s360', 'big'))
            for image in item.get('image_urls', [])
        ]

        yield item
