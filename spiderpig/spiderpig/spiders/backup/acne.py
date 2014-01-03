import itertools

from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from spiderpig.spiders import BaseSpider
from spiderpig.items import Product, ProductLoader


class AcneSpider(BaseSpider):
    name = 'acne'
    allowed_domains = ['shop.acnestudios.com']
    start_urls = [
        'http://shop.acnestudios.com/shop-women/',
        'http://shop.acnestudios.com/shop-men/',
        'http://shop.acnestudios.com/sale-women/',
        'http://shop.acnestudios.com/sale-men/',
    ]
    rules = [
        Rule(SgmlLinkExtractor(allow=['/shop/.+\.html']), callback='parse_product', follow=True),
    ]

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response).select('//body[contains(@class, "catalog-product-view")]')
        if not hxs:
            item = Product()
            item['key'] = response.url
        else:
            item = self._parse_product(response, hxs)

        yield item

    def _parse_product(self, response, hxs):
        l = ProductLoader(item=Product(), selector=hxs)
        l.add_xpath('name', '//h1/text()')
        l.add_xpath('description', '//div[contains(@class, "description")]/div/text()')
        l.add_xpath('discount_price', '//p[contains(@class, "price")]/span/text()')
        l.add_xpath('regular_price', '//p[contains(@class, "price")]/span/span/text()')
        l.add_xpath('image_urls', '//div[contains(@class, "product-image")]//img/@src')
        l.add_xpath('in_stock', '//select[contains(@id, "product-size-id")]/option[position()>1][not(contains(@class, "inactive"))]')

        l.add_value('url', response.url)
        l.add_value('category', ' / '.join(response.url.split('/')[3:-1]))
        l.add_value('key', response.url)
        l.add_value('affiliate', 'cj')
        l.add_value('vendor', AcneSpider.name)
        l.add_value('brand', 'Acne')

        base_url = get_base_url(response)

        item = l.load_item()
        item['in_stock'] = bool(item.get('in_stock'))
        item['image_urls'] = [
            urljoin_rfc(base_url, image)
            for image in item.get('image_urls', [])
        ]

        return item
