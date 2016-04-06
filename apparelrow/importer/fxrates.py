import logging, re, os
from decimal import Decimal

from lxml import etree

from apparelrow.importer.framework import fetcher
from apparelrow.importer.models import FXRate


logger = logging.getLogger('apparel.importer.fxrates')

class FXRateImporter():
    """
    Handling fx rates from imported xml file. Does not work presently
    """
    def __init__(self, file=None, url=None, base_currency=None):
        self.file = file
        self.url  = url
        self.base_currency = base_currency

    def run(self):
        if self.file:
            logger.info("Refreshing FX rates from local file %s", self.file)
            return self.import_feed(self.file)
        else:
            logger.info("Refreshing FX rates from URL %s", self.url)
            feed_file = fetcher.fetch(self.url)
            try:
                feed = self.import_feed(feed_file)
                return feed
            finally:
                os.remove(feed_file)

    def import_fx_rate(self, currency, rate):
        fxrate = None
        mode   = ""

        try:
            fxrate = FXRate.objects.get(
                currency=currency,
                base_currency=self.base_currency
            )
            mode = "Updated"
        except FXRate.DoesNotExist:
            fxrate = FXRate(
                currency=currency,
                base_currency=self.base_currency
            )
            mode = "Created"

        # FIXME: Loggin
        if not isinstance(rate, Decimal):
            rate = Decimal(str(rate))

        fxrate.rate = rate
        fxrate.save()
        logger.debug(u"%s %s", mode, fxrate)

        return fxrate

    def import_feed(self, rss_file):
        doc = etree.parse(rss_file)

        re_curr = re.compile(r'^([A-Z]{3})/')
        re_rate = re.compile(r'^1.+?=\s*([0-9\.]+)')
        count   = 0

        for item in doc.xpath('//item'):
            currency = re_curr.search(item.xpath('./title')[0].text)
            if not currency: continue

            rate = re_rate.search(item.xpath('./description')[0].text)
            if not rate: continue

            self.import_fx_rate(currency.group(1), rate.group(1))
            count += 1

        logger.info("%i FX rates refreshed", count)
        return True

class FXRateImporterParseError(Exception):
    pass

