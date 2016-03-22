import hashlib
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
        return self.data.get(ProductItem.KEY_SITE_PRODUCT, None)

    def set_site_product(self, site_product_pk):
        if not site_product_pk:
            if ProductItem.KEY_SITE_PRODUCT in self.data:
                self.data.pop(ProductItem.KEY_SITE_PRODUCT)
        else:
            self.data[ProductItem.KEY_SITE_PRODUCT] = site_product_pk


def get_product_hash(item_subset):
    """
    Creating a data sig for product dict values in ProductItem
    :param item_subset:
    :return:
    """
    include = ("sku", "name", "url", "category", "description", "brand", "gender", "colors", "regular_price",
               "discount_price", "currency", "in_stock", "stock")
    attributes = []
    for key in include:
        attributes.append(repr(item_subset.get(key)))
    return hashlib.sha1("".join(attributes)).hexdigest()


def get_site_product_hash(site_product, **kwargs):
    """
    Creating a data sig for site product, violates DRY principle on this experimental stage. Need refactoring later.
    :param site_product:
    :return:
    """
    include = ("product_name", "product_key", "description", "category_id", "manufacturer_id", "sku", "static_brand", "gender", "availability",)
    kwarg_keys = ("regular_price", "discount_price", "currency", "in_stock", "colors")
    attributes = []
    for key in include:
        attributes.append(repr(getattr(site_product, key)))

    # Kwargs contain data from ProductItem.Final
    if kwargs:
        for key in kwarg_keys:
            attributes.append(repr(kwargs.get(key)))
    return hashlib.sha1("".join(attributes)).hexdigest()