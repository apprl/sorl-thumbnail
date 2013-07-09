import itertools

from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.contrib.loader.processor import Join

from scrapy.contrib.spiders import CrawlSpider

from spiderpig.spiders import BaseSpider
from spiderpig.items import Product, ProductLoader


class OkiNiSpider(BaseSpider):
    name = 'oki_ni'
    allowed_domains = ['oki-ni.com']
    start_urls = [
        'http://www.oki-ni.com/latestproducts/',
    ]
    # Exclude jp-jp links and links changing currency
    rules = [
        Rule(SgmlLinkExtractor(deny=['\?currency=', 'jp-jp'], allow=['/.+\.html']), callback='parse_product', follow=True),
    ]

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response).select('//div[contains(concat(" ", normalize-space(@class), " "), " details_product ")]')
        if not hxs:
            item = Product()
            item['key'] = response.url
        else:
            item = self._parse_product(response, hxs)

        yield item

    def _parse_product(self, response, hxs):
        categories = HtmlXPathSelector(response).select('//div[contains(@class, "template_breadcrumb")]//a/text()').extract()

        regular_price = hxs.select('//span[contains(@class, "details_price_rrp")]/span/text()').extract()
        if not regular_price:
            regular_price = hxs.select('//div[contains(@class, "details_price")]/p/text()').extract()

        l = ProductLoader(item=Product(), selector=hxs)
        l.add_xpath('name', '//h1[contains(@class, "product_name")]/text()')
        l.add_xpath('brand', '//h1/a/text()')
        l.add_xpath('image_urls', '//div[contains(@class, "details_images")]//li//img/@src')
        l.add_xpath('description', '//div[contains(@id, "accordion")]/div[2]//p/text()', Join())
        l.add_xpath('discount_price', '//p[contains(@class, "details_price_now")]/text()')
        l.add_xpath('in_stock', '//p[contains(@class, "details_instock")]')

        l.add_value('gender', 'M')
        l.add_value('regular_price', regular_price)
        l.add_value('category', '/'.join(categories))
        l.add_value('url', response.url)
        l.add_value('key', response.url)
        l.add_value('affiliate', 'affiliatewindow')
        l.add_value('vendor', OkiNiSpider.name)

        # Missing: colors

        item = l.load_item()
        item['in_stock'] = bool(item.get('in_stock'))
        item['image_urls'] = ['%s?$press$' % (image,) for image in item.get('image_urls', [])]

        return item
