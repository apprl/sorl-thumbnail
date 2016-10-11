# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

from cStringIO import StringIO
from scrapy.utils.spider import iterate_spider_output
from scrapy import Spider
from scrapy.exceptions import NotConfigured
import simplejson
from zipfile import ZipFile


def unzip(data):
    """
    Unzip the given data and return as much data as possible.
    Expects a str.
    """
    f = ZipFile(StringIO(data))
    output = ''
    for tmpfile in f.infolist():
        output += f.open(tmpfile).read()
    return output


def is_zipped(response):
    """Return True if the response is zipped, or False otherwise"""
    ctype = response.headers.get('Content-Type', '')
    return ctype in ('application/zip',)


class JSONFeedSpider(Spider):
    """
    This class intends to be the base class for spiders that scrape
    from JSON feeds.

    You can choose whether to parse the file using the 'iternodes' iterator, an
    'xml' selector, or an 'html' selector.  In most cases, it's convenient to
    use iternodes, since it's a faster and cleaner.
    """

    headers = None
    itertag = None

    def process_results(self, response, results):
        """This method has the same purpose as the one in XMLFeedSpider"""
        return results

    def adapt_response(self, response):
        """This method has the same purpose as the one in XMLFeedSpider"""
        return response

    def parse_row(self, response, row):
        """This method must be overriden with your custom spider functionality"""
        raise NotImplementedError

    def parse_rows(self, response):
        """Receives a response and a dict (representing each row) with a key for each provided (or detected)
        header of the CSV file.  This spider also gives the opportunity to override adapt_response and process_results
        methods for pre and post-processing purposes.
        """
        json_data = simplejson.loads(response.body)
        if self.itertag:
            rows = json_data.get(self.itertag, None)
            if not rows:
                rows = json_data
        else:
            rows = json_data

        for row in rows:
            ret = iterate_spider_output(self.parse_row(response, row))
            for result_item in self.process_results(response, ret):
                yield result_item

    def parse(self, response):
        if not hasattr(self, 'parse_row'):
            raise NotConfigured('You must define parse_row method in order to scrape this CSV feed')
        response = self.adapt_response(response)
        return self.parse_rows(response)

