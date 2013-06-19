from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from spiderpig.items import Product, ProductLoader
from spiderpig.utils import generate_buy_url


class AcneSpider(CrawlSpider):
    name = 'acne'
    allowed_domains = ['shop.acnestudios.com']
    start_urls = [
        'http://shop.acnestudios.com/shop/women/dresses.html',
    ]
    rules = [Rule(SgmlLinkExtractor(allow=['/shop/.+\.html']), 'parse_product')]

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response).select('//body[contains(@class, "catalog-product-view")]')
        if not hxs:
            return

        l = ProductLoader(item=Product(), selector=hxs)
        l.add_xpath('name', '//h1/text()')
        l.add_xpath('description', '//div[contains(@class, "description")]/div/text()')
        l.add_xpath('price', '//p[contains(@class, "price")]/span/text()')
        l.add_xpath('regular_price', '//p[contains(@class, "price")]/span/span/text()')
        l.add_xpath('image_urls', '//div[contains(@class, "product-image")]//img/@src')
        # TODO: for now it seems like all products found are in stock
        l.add_value('in_stock', 'in-stock')
        l.add_value('url', response.url)
        l.add_value('category', ' / '.join(response.url.split('/')[3:-1]))
        l.add_value('identifier', response.url.split('/')[-1])
        l.add_value('affiliate', 'cj')
        l.add_value('vendor', AcneSpider.name)
        l.add_value('brand', 'Acne')

        base_url = get_base_url(response)

        item = l.load_item()
        item['in_stock'] = bool(item['in_stock'])
        item['image_urls'] = [
            urljoin_rfc(base_url, image)
            for image in item.get('image_urls', [])
        ]

        yield item
