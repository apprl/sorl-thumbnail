import json
import logging


logger = logging.getLogger(__name__)


class ProductItem:
    KEY_SCRAPED = 'scraped'
    KEY_PARSED = 'parsed'
    KEY_MANUAL = 'manual'
    KEY_FINAL = 'final'
    KEY_SITE_PRODUCT = 'site_product'

    def __init__(self, product):
        self.product = product
        try:
            self.data = json.loads(self.product.json)
        except (AttributeError, TypeError, ValueError):
            logger.exception('Could not parse JSON [Product: %s - %s]' % (self.product.pk, self.product.product_name))

    def validate_keys(self):
        for key in [ProductItem.KEY_SCRAPED, ProductItem.KEY_PARSED, ProductItem.KEY_FINAL]:
            if key not in self.data:
                return False
        return True

    def save(self):
        self.product.json = json.dumps(self.data)
        self.product.save()

    def get(self, layer, attribute, default=None):
        layer = self.data.get(layer, default)
        if layer:
            return layer.get(attribute, default)

    def get_scraped(self, attribute, default=None):
        return self.get(ProductItem.KEY_SCRAPED, attribute, default)

    def get_parsed(self, attribute, default=None):
        return self.get(ProductItem.KEY_MANUAL, attribute, default) or self.get(ProductItem.KEY_PARSED, attribute, default)

    def get_final(self, attribute, default=None):
        return self.get(ProductItem.KEY_FINAL, attribute, default)

    def set_scraped(self, attribute, value):
        self.data[ProductItem.KEY_SCRAPED][attribute] = value

    def get_site_product(self):
        return self.data.get(ProductItem.KEY_SITE_PRODUCT)

    def set_site_product(self, site_product_pk):
        if not site_product_pk:
            if ProductItem.KEY_SITE_PRODUCT in self.data:
                self.data.pop(ProductItem.KEY_SITE_PRODUCT)
        else:
            self.data[ProductItem.KEY_SITE_PRODUCT] = site_product_pk
