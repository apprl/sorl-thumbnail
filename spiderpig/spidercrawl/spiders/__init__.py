import itertools
import re
import urllib

from django.utils.encoding import force_bytes

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


class KeyExtractorMixin:

    url_last_regex = re.compile(r'\?url=(.+)$')

    def get_url_last(self, url):
        result = self.url_last_regex.search(url)
        if result:
            return urllib.unquote(force_bytes(result.group(1)))
        return key


class BaseSpider(CrawlSpider):

    def parse(self, response):
        return itertools.chain(CrawlSpider.parse(self, response), self.parse_product(response))
