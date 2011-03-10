import libxml2, logging, re
from decimal import Decimal
from xml.sax.saxutils import unescape

from importer.framework import fetcher
from importer.models import FXRate

class FXRateImporter():
    def __init__(self, file=None, url=None, base_currency=None):
        self.file = file
        self.url  = url
        self.base_currency = base_currency
    
    def run(self):
        if self.file:
            return self.import_feed(self.file)
        else:
            return self.import_feed(fetcher.fetch(self.url))
        
    def import_fx_rate(self, currency, rate):
        fxrate = None
        try:
            fxrate = FXRate.objects.get(
                currency=currency, 
                base_currency=self.base_currency
            )
        except FXRate.DoesNotExist:
            fxrate = FXRate(
                currency=currency, 
                base_currency=self.base_currency
            )
        
        # FIXME: Loggin
        if not isinstance(rate, Decimal):
            rate = Decimal(str(rate))
                
        fxrate.rate = rate
        fxrate.save()
        
        return fxrate
    
    def import_feed(self, rss_file):
        doc = libxml2.readFile(rss_file, 'utf8', libxml2.XML_PARSE_NOENT)
        ctx = doc.xpathNewContext()
        
        re_curr = re.compile(r'^([A-Z]{3})/')
        re_rate = re.compile(r'^1.+?=\s*([0-9\.]+)')
        
        for item in ctx.xpathEval('//item'):
            currency = re_curr.search(item.xpathEval('./title')[0].getContent())
            if not currency: continue
                        
            rate = re_rate.search(item.xpathEval('./description')[0].getContent())
            if not rate: continue
            
            self.import_fx_rate(currency.group(1), rate.group(1))
        
        return True
