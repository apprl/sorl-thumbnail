import itertools

from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc


from scrapy.contrib.spiders import CrawlSpider

from spiderpig.spiders import BaseSpider
from spiderpig.items import Product, ProductLoader


class SneakersnstuffSpider(BaseSpider):
    name = 'sneakersnstuff'
    allowed_domains = ['sneakersnstuff.com']
    start_urls = [
        'http://www.sneakersnstuff.com/en/54/clothes',
        'http://www.sneakersnstuff.com/en/2/sneakers',
    ]
    rules = [
        Rule(SgmlLinkExtractor(allow=['/en/product/.+']), callback='parse_product', follow=True),
    ]

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response).select('//body[contains(@class, "product-view")]')
        if not hxs:
            item = Product()
            item['key'] = response.url
        else:
            item = self._parse_product(response, hxs)

        yield item

    def _parse_product(self, response, hxs):
        product_price = hxs.select('//div[contains(@class, "product-price")]')
        discount_price = []
        regular_price = product_price.select('span[contains(@class, "price")]/text()').extract()
        if not regular_price:
            discount_price = product_price.select('span[contains(@class, "sale")]/text()').extract()
            regular_price = product_price.select('del[contains(@class, "sale")]/text()').extract()

        l = ProductLoader(item=Product(), selector=hxs)
        l.add_xpath('name', '//h1[contains(@id, "product-name")]/text()[preceding-sibling::br]')
        l.add_xpath('brand', '//h1[contains(@id, "product-name")]/text()[following-sibling::br]')
        l.add_xpath('colors', '//span[contains(@id, "product-color")]/text()')
        l.add_xpath('gender', '//div[contains(@id, "product-info-gender-image")]/img/@src')
        l.add_xpath('image_urls', '//div[contains(@id, "thumbnail-wrapper")]/a/@href')

        l.add_value('regular_price', regular_price)
        l.add_value('discount_price', discount_price)
        l.add_value('category', 'undefined')
        l.add_value('in_stock', 'in-stock')
        l.add_value('description', '')
        l.add_value('url', response.url)
        l.add_value('key', response.url)
        l.add_value('affiliate', 'cj')
        l.add_value('vendor', SneakersnstuffSpider.name)

        base_url = get_base_url(response)

        item = l.load_item()
        item['in_stock'] = bool(item.get('in_stock'))
        item['colors'] = item.get('colors', '').split('/')
        item['image_urls'] = [
            urljoin_rfc(base_url, image)
            for image in item.get('image_urls', [])
        ]

        return item
