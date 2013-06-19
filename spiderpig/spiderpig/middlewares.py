import random

from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.utils.url import url_is_from_spider
from scrapy.http import HtmlResponse
from scrapy import log

from spiderpig.settings import USER_AGENT_LIST


class RelCanonicalMiddleware(object):
    _extractor = SgmlLinkExtractor(restrict_xpaths=['//head/link[@rel="canonical"]'], tags=['link'], attrs=['href'])

    def process_response(self, request, response, spider):
        if isinstance(response, HtmlResponse) and response.body and getattr(spider, 'follow_canonical_links', False):
            rel_canonical = self._extractor.extract_links(response)
            if rel_canonical:
                rel_canonical = rel_canonical[0].url
                if rel_canonical != request.url and url_is_from_spider(rel_canonical, spider):
                    log.msg('Redirecting (rel="canonical") to %s from %s' % (rel_canonical, request), level=log.DEBUG, spider=spider)
                    return request.replace(url=rel_canonical, callback=lambda r: r if r.status == 200 else response)

        return response


class RandomUserAgentMiddleware:

    def process_request(self, request, spider):
        ua = random.choice(USER_AGENT_LIST)
        request.headers.setdefault('User-Agent', ua)
        log.msg('Using random UA: %s' % (ua,))
