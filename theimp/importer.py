import logging
import os.path

from django.conf import settings
from django.db.models.loading import get_model
from django.template.defaultfilters import slugify

from hotqueue import HotQueue

from theimp.utils import load_product_json


logger = logging.getLogger(__name__)


class Importer(object):

    def __init__(self, site_queue=None):
        self.imp_product_model = get_model('theimp', 'Product')
        self.site_product_model = get_model('apparel', 'Product')
        self.vendor_product_model = get_model('apparel', 'VendorProduct')
        if not site_queue:
            self.site_queue = HotQueue(settings.THEIMP_QUEUE_SITE,
                                       host=settings.THEIMP_REDIS_HOST,
                                       port=settings.THEIMP_REDIS_PORT,
                                       db=settings.THEIMP_REDIS_DB)
        else:
            self.site_queue = site_queue

    def run(self):
        for product_id, is_valid in self.site_queue.consume():
            logger.debug('Consume from site queue: (%s, %s)' % (product_id, is_valid))
            try:
                product = self.imp_product_model.objects.get(pk=product_id)
            except self.imp_product_model.DoesNotExist as e:
                logger.exception('Could not load product with id %s' % (product_id,))
                continue

            product_final_json = load_product_json(product, layer='final')
            site_product = self._find_site_product(product_final_json)

            try:
                if is_valid:
                    if site_product:
                        self.update_product(product, site_product, product_final_json)
                    else:
                        self.add_product(product, product_final_json)
                else:
                    self.hide_product(product, site_product)
            except Exception as e:
                logger.exception('Could not import product to site: %s' % (product,))
            else:
                # XXX: Is this for updating of modified datetime?
                product.save()

    def add_product(self, product, product_json):
        site_product = self.site_product_model.objects.create(
            product_name = product_json.get('name'),
            description = product_json.get('description'),
            category_id = product_json.get('category_id'),
            manufacturer_id = product_json.get('brand_id'),
            static_brand = product_json.get('brand'),
            gender = product_json.get('gender'),
            availability = bool(product_json.get('in_stock', False)),
            product_image = self._product_image(product_json)
        )

        self._update_vendor_product(product_json, site_product)
        self._update_product_options(product_json, site_product)

        logger.info('[%s] Add product to live site: %s' % (product.pk, site_product))

    def update_product(self, product, site_product, product_json):
        site_product.product_name = product_json.get('name')
        site_product.description = product_json.get('description')
        site_product.category_id = product_json.get('category_id')
        site_product.manufacturer_id = product_json.get('brand_id')
        site_product.static_brand = product_json.get('brand')
        site_product.gender = product_json.get('gender')
        site_product.availability = bool(product_json.get('in_stock', False))
        site_product.product_image = self._product_image(product_json)
        site_product.save()

        self._update_vendor_product(product_json, site_product)
        self._update_product_options(product_json, site_product)

        logger.info('[%s] Update product on live site: %s' % (product.pk, site_product))

    def hide_product(self, product, site_product):
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

    def _product_image(self, product_json):
        # TODO: only returns first product image for now
        return os.path.join(settings.APPAREL_PRODUCT_IMAGE_ROOT,
                            product_json.get('images')[0]['path'])

    def _update_product_options(self, product_json, site_product):
        # TODO: product options
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
        # XXX: price, currency and discount_price should not be used, WHY???
        #vendor_product.price = product_json.get('regular_price') or '0.0'
        #vendor_product.currency = product_json.get('currency')
        #vendor_product.discount_price = product_json.get('discount_price')
        vendor_product.save()

    def _find_site_product(self, product_json):
        """
        Find a product on the live site by slug.
        """
        if product_json:
            slug = slugify('%s-%s' % (product_json.get('brand'), product_json.get('name')))
            try:
                return self.site_product_model.objects.get(slug=slug)
            except self.site_product_model.DoesNotExist:
                logger.debug('Could not find product with slug %s' % (slug,))

        return None
