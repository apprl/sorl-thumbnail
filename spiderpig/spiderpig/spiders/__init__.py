import itertools

from scrapy.contrib.spiders import CrawlSpider


class AffiliateMixin(object):
    AFFILIATE_AAN = 'aan'
    AFFILIATE_CJ = 'cj'
    AFFILIATE_TRADEDOUBLER = 'tradedoubler'
    AFFILIATE_AW = 'affiliatewindow'
    AFFILIATE_ZANOX = 'zanox'


class BaseSpider(CrawlSpider):

    def parse(self, response):
        return itertools.chain(CrawlSpider.parse(self, response), self.parse_product(response))
