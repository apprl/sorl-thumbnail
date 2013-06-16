import random

from scrapy import log

from spiderpig.settings import USER_AGENT_LIST

class RandomUserAgentMiddleware:

    def process_request(self, request, spider):
        ua = random.choice(USER_AGENT_LIST)
        request.headers.setdefault('User-Agent', ua)
        log.msg('Using random UA: %s' % (ua,))
