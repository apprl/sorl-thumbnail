import logging
import json

from django.conf import settings
from django.db.models.loading import get_model
from django.template.defaultfilters import slugify

from hotqueue import HotQueue


logger = logging.getLogger(__name__)


class Importer(object):

    def __init__(self):
        self.imp_product_model = get_model('theimp', 'Product')
        self.site_product_model = get_model('apparel', 'Product')
        self.vendor_product_model = get_model('apparel', 'VendorProduct')
        self.site_queue = HotQueue(settings.THEIMP_QUEUE_SITE,
                                   host=settings.THEIMP_REDIS_HOST,
                                   port=settings.THEIMP_REDIS_PORT,
                                   db=settings.THEIMP_REDIS_DB)

    def run(self):
        for product_id, is_valid in self.site_queue.consume():
            logger.debug('Consume from queue: (%s, %s)' % (product_id, is_valid))
            try:
                product = self.imp_product_model.objects.get(pk=product_id)
            except self.imp_product_model.DoesNotExist as e:
                logger.exception('Could not load imp product with id %s' % (product_id,))
                continue

            try:
                if is_valid:
                    self.add_or_update(product)
                else:
                    self.hide_product(product)
            except Exception as e:
                logger.exception('Could not import product to site: %s' % (product,))
            else:
                product.save()

    def add_or_update(self, product):
        site_product = self._find_site_product(product)
        if site_product:
            self.update_product(product, site_product)
        else:
            self.add_product(product)

    def add_product(self, product):
        product_json = self._load_json(product, layer='final')

        # TODO: product image
        site_product = self.site_product_model.create(
            product_name = product_json.get('name'),
            description = product_json.get('description'),
            category = product_json.get('category_id'),
            manufacturer = product_json.get('brand_id'),
            static_brand = product_json.get('brand'),
            gender = product_json.get('gender'),
            availability = bool(product_json.get('in_stock', False))
        )

        self._update_vendor_product(product_json, site_product)

        # TODO: product options
        self._update_product_options(product_json, site_product)

        logger.info('[%s] Add product to live site: %s' % (product.pk, site_product))

    def update_product(self, product, site_product):
        product_json = self._load_json(product, layer='final')

        # Product update
        # TODO: product_image
        site_product.product_name = product_json.get('name')
        site_product.description = product_json.get('description')
        site_product.category_id = product_json.get('category_id')
        site_product.manufacturer_id = product_json.get('brand_id')
        site_product.static_brand = product_json.get('brand')
        site_product.gender = product_json.get('gender')
        site_product.availability = bool(product_json.get('in_stock', False))

        self._update_vendor_product(product_json, site_product)

        # TODO: product options
        self._update_product_options(product_json, site_product)

        site_product.save()

        logger.info('[%s] Update product on live site: %s' % (product.pk, site_product))

    def hide_product(self, product):
        site_product = self._find_site_product(product)
        if site_product:
            site_product.availability = False
            for vendor_product in site_product.vendorproduct.all():
                vendor_product.availability = 0
                vendor_product.save()
            site_product.save()
            logger.info('[%s] Hide product on live site: %s' % (product.pk, site_product))
        else:
            logger.warning('[%s] Could not find a product to hide on live site' % (product.pk,))


    #
    # HELPERS
    #

    def _update_product_options(self, product_json, site_product):
        pass

    def _update_vendor_product(self, product_json, site_product):
        vendor_product, _ = self.vendor_product_model.objects.get_or_create(
            product=site_product, vendor_id=product_json.get('vendor_id'),
        )
        vendor_product.buy_url = product_json.get('buy_url')
        vendor_product.original_price = product_json.get('regular_price') or '0.0'
        vendor_product.original_currency = product_json.get('currency')
        vendor_product.original_discount_price = product_json.get('discount_price')
        vendor_product.original_discount_currency = product_json.get('currency')
        vendor_product.availability = bool(product_json.get('in_stock', False))
        # XXX: price, currency and discount_price should not be used
        #vendor_product.price = product_json.get('regular_price') or '0.0'
        #vendor_product.currency = product_json.get('currency')
        #vendor_product.discount_price = product_json.get('discount_price')
        vendor_product.save()

    def _load_json(self, product, layer=None):
        item = None
        try:
            item = json.loads(product.json)
        except (ValueError, AttributeError) as e:
            logger.exception('Could not parse JSON [Product ID: %s]' % (product.pk,))

        if item:
            if layer:
                return item.get(layer)

            item_layer = item.get('final')
            if not item_layer:
                item_layer = item.get('parsed')

            return item_layer

        return None

    def _find_site_product(self, product):
        """
        Find a product on the live site by slug.
        """
        product_json = self._load_json(product)
        if product_json:
            slug = slugify('%s-%s' % (product_json.get('brand'), product_json.get('name')))
            try:
                return self.site_product_model.objects.get(slug=slug)
            except self.site_product_model.DoesNotExist:
                pass

        return None
