import itertools

from scrapy.contrib.spiders import CrawlSpider


class AffiliateMixin(object):
    AFFILIATE_AAN = 'aan'
    AFFILIATE_CJ = 'cj'
    AFFILIATE_TRADEDOUBLER = 'tradedoubler'
    AFFILIATE_AW = 'affiliatewindow'
    AFFILIATE_ZANOX = 'zanox'
    AFFILIATE_LINKSHARE = 'linkshare'


class PriceMixin:
    def parse_price(self, price):
        if not price:
            return (None, None)
        elif price[-3:] in ['SEK', 'EUR', 'GBP', 'USD']:
            currency = price[-3:]
            price = price[:-3]
            return (price.strip(), currency.strip())
        elif ' ' in price:
            return price.split(' ', 1)

        return (price, None)


class BaseSpider(CrawlSpider):

    def parse(self, response):
        return itertools.chain(CrawlSpider.parse(self, response), self.parse_product(response))
