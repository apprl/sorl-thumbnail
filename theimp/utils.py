import json
import logging


logger = logging.getLogger(__name__)


def load_product_json(product, layer=None):
    item = None
    try:
        item = json.loads(product.json)
    except (ValueError, TypeError, AttributeError) as e:
        logger.exception('Could not parse JSON [Product ID: %s, Key: %s]' % (product.pk, product.key))

    if item:
        if layer:
            return item.get(layer)

        return item

    return None
