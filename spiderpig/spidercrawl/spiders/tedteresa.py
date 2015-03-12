from scrapy.contrib.spiders import XMLFeedSpider

from spiderpig.spidercrawl.items import Product, ProductLoader
from spiderpig.spidercrawl.spiders import AffiliateMixin, PriceMixin
#from spiderpig.utils import ApprlFileLogObserver,WARNING,INFO
from scrapy import log
import os
from twisted.python.logfile import DailyLogFile

class TedTeresaSpider(XMLFeedSpider, AffiliateMixin, PriceMixin):
    name = 'ted-teresa'
    allowed_domains = ['tedteresa.com']
    start_urls = ['https://tedteresa.com/feeds/GoogleShopping.xml']
    namespaces = [('g', 'http://base.google.com/ns/1.0')]
    itertag = 'item'

    """def __init__(self, name=None, **kwargs):
        loglevel = WARNING
        file_to_write = os.path.join(os.path.abspath(os.path.dirname(__file__)),'../logs/%s.log' % self.name)
        logencoding = "utf-8"
        crawler = name
        sflo = ApprlFileLogObserver(DailyLogFile.fromFullPath(file_to_write), loglevel, logencoding, crawler)
        log.log.addObserver(sflo.emit)
        super(JcSpider, self).__init__(name, **kwargs)
    """
    def parse_node(self, response, node):
        try:
            in_stock = node.xpath('g:availability/text()').extract()[0]
            if in_stock:
                in_stock = in_stock.strip()

            regular_price = node.xpath('g:price/text()').extract()

            currency = None
            if regular_price:
                regular_price, currency = self.parse_price(regular_price[0])

            if not currency:
                currency = 'SEK'

            discount_price = node.xpath('g:sale_price/text()').extract()
            if discount_price:
                discount_price, _ = self.parse_price(discount_price[0])
            else:
                discount_price = regular_price
            product_type = u'%s' % node.xpath('g:product_type/text()').extract()[0]

            gender = "U"
            categories = product_type.split(u" > ")
            category = categories[0]
            gender = categories[1]
            if gender == "Man":
                gender = "M"
            elif gender == "Kvinna":
                gender = "W"
            log.msg(message='CATEGORIES: %s \nExtracted gender %s' % (categories,gender) )

            # Select image ending with _90 if it exists
            images = node.xpath('g:image_link/text()').extract()
            extra_images = node.xpath('g:additional_image_link/text()').extract()
            for image in extra_images:
                if '_90' in image:
                    images = [image]
                    break

            l = ProductLoader(item=Product(), selector=node)
            # Url key for the product
            l.add_xpath('key', 'link/text()')
            # Article id from the vendor. To make sure the products are unique on the page/ product table.
            l.add_xpath('sku', 'g:id/text()')
            # Name of product
            l.add_xpath('name', 'title/text()')
            # Name of the vendor, predefined in the file
            l.add_value('vendor', self.name)
            # Url of the product, stripped of extra information that is passed along?
            l.add_xpath('url', 'link/text()')
            # Affiliate id if the contact is established through another partner
            l.add_value('affiliate', self.AFFILIATE_AAN)
            # Category to describe the product in a context, used to match the product category to existing categories (Normalization)
            l.add_value('category', category)
            # Descriptive text about the product
            l.add_xpath('description', 'description/text()')
            # Brand name of the product
            l.add_xpath('brand', 'g:brand/text()')
            # Gender, can be U, M or W. Will map the value in the imp importer.
            l.add_value('gender', gender)
            # Color of the product. Can be multiple?
            l.add_xpath('colors', 'g:color/text()')
            # Regular price
            l.add_value('regular_price', regular_price)
            # How does the system react to discount price, non existant, is the same as regular price, is None etc?
            l.add_value('discount_price', discount_price)
            # Currency of the product
            l.add_value('currency', currency)
            # Is in stock at all, how does the system handle these ones?
            l.add_value('in_stock', True if in_stock == 'in stock' else False)
            # The amount of articles in stock. How does the system handle this if this is none, '' or 0?
            l.add_value('stock', '-1')
            l.add_value('image_urls', images)

            return l.load_item()
        except:
            pass
