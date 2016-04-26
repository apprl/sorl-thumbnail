import hashlib
import json
import logging
from django.utils.encoding import force_text
from django.utils.html import strip_tags


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
    include = ("sku", "name", "url", "category", "brand", "regular_price",
               "discount_price", "currency", "in_stock")
    attributes = []
    for key in include:
        field = stringify( item_subset.get(key) )
        attributes.append(field)
    #logger.info(attributes)
    return hashlib.sha1("".join(attributes)).hexdigest()

def stringify(field, cleantags=False):
    """
    Prepares the field to get serialized for hashing.
    :param field:
    :return:
    """
    try:
        field = field.decode("utf8")
    except:
        pass

    try:
        field = str(field.encode("utf8"))
    except:
        pass

    if not field or isinstance(field, bool) or isinstance(field, int):
        field = str(field)
        return field

    elif isinstance(field, list) or isinstance(field, tuple):
        field = [stringify(unit) for unit in field]
        return ",".join(field)
    else:
        if cleantags:
            field = strip_tags(field).strip()
        return field

def compare_scraped_and_saved(item_scraped, product_scraped):
    include = ("sku", "name", "url", "category", "description", "brand", "gender", "colors", "regular_price",
               "discount_price", "currency", "in_stock", "stock")

    attributes = []
    for key in include:
        scraped_field = stringify( item_scraped.get(key) )
        product_field = stringify( product_scraped.get(key) )

        if not scraped_field == product_field:
            if key == "description":
                attributes.append((key, "Description changed", "Description changed"))
            else:
                attributes.append((key, scraped_field, product_field))
            logger.info("{} not equals {}".format(scraped_field, product_field))
    return attributes

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
        attributes.append(stringify(getattr(site_product, key)))

    # Kwargs contain data from ProductItem.Final
    if kwargs:
        for key in kwarg_keys:
            attributes.append(stringify(kwargs.get(key)))
    return hashlib.sha1("".join(attributes)).hexdigest()