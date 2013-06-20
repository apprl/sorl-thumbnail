import itertools

from scrapy.contrib.spiders import CrawlSpider


class BaseSpider(CrawlSpider):

    def parse(self, response):
        return itertools.chain(CrawlSpider.parse(self, response), self.parse_product(response))
