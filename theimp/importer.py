import logging
import os.path
import re

from django.conf import settings
from django.db.models.loading import get_model
from django.template.defaultfilters import slugify

from hotqueue import HotQueue

from theimp.models import Vendor
from theimp.utils import ProductItem


logger = logging.getLogger(__name__)


class Importer(object):

    def __init__(self, site_queue=None):
        self.product_model = get_model('theimp', 'Product')
        self.site_product_model = get_model('apparel', 'Product')
        self.vendor_product_model = get_model('apparel', 'VendorProduct')
        self.site_option_model = get_model('apparel', 'Option')
        self.site_brand_model = get_model('apparel', 'Brand')
        self.site_category_model = get_model('apparel', 'Category')

        self.option_types = dict([(re.sub(r'\W', '', v.name.lower()), v) for v in get_model('apparel', 'OptionType').objects.iterator()])

        self.site_queue = HotQueue(settings.THEIMP_QUEUE_SITE,
                                   host=settings.THEIMP_REDIS_HOST,
                                   port=settings.THEIMP_REDIS_PORT,
                                   db=settings.THEIMP_REDIS_DB)
        if site_queue:
            self.site_queue = site_queue

    def run(self):
        for product_id, is_valid in self.site_queue.consume():
            logger.debug('Consume from site queue: (%s, %s)' % (product_id, is_valid))
            try:
                product = self.product_model.objects.get(pk=product_id)
            except self.product_model.DoesNotExist as e:
                logger.exception('Could not load product with id %s' % (product_id,))
                continue

            item = ProductItem(product)
            site_product = self._find_site_product(item)
            if site_product:
                item.set_site_product(site_product.pk)
                item.save()

            try:
                if is_valid:
                    if site_product:
                        self.update_product(item, site_product)
                    else:
                        self.add_product(item)
                else:
                    if site_product:
                        self.hide_product(site_product)
            except Exception as e:
                logger.exception('Could not import product to site with id %s' % (product_id,))
            else:
                # XXX: Is this for updating of modified datetime?
                product.save()

    def add_product(self, item):
        brand, _ = self.site_brand_model.objects.get_or_create(name=item.get_final('brand'))
        category, _ = self.site_category_model.objects.get_or_create(name=item.get_final('category'), name_order=item.get_final('category'))

        site_product = self.site_product_model.objects.create(
            product_name = item.get_final('name'),
            description = item.get_final('description'),
            category = category,
            manufacturer = brand,
            static_brand = item.get_final('brand'),
            gender = item.get_final('gender'),
            availability = bool(item.get_final('in_stock', False)),
            product_image = self._product_image(item)
        )

        self._update_vendor_product(item, site_product)
        self._update_product_options(item, site_product)

    def update_product(self, item, site_product):
        brand, _ = self.site_brand_model.objects.get_or_create(name=item.get_final('brand'))
        category, _ = self.site_category_model.objects.get_or_create(name=item.get_final('category'), name_order=item.get_final('category'))

        site_product.product_name = item.get_final('name')
        site_product.description = item.get_final('description')
        site_product.category = category
        site_product.manufacturer = brand
        site_product.static_brand = item.get_final('brand')
        site_product.gender = item.get_final('gender')
        site_product.availability = bool(item.get_final('in_stock', False))
        site_product.product_image = self._product_image(item)
        site_product.save()

        self._update_vendor_product(item, site_product)
        self._update_product_options(item, site_product)

    def hide_product(self, site_product):
        site_product.availability = False
        for vendor_product in site_product.vendorproduct.all():
            vendor_product.availability = 0
            vendor_product.save()
        site_product.save()


    #
    # HELPERS
    #

    def _product_image(self, item):
        return os.path.join(settings.APPAREL_PRODUCT_IMAGE_ROOT, item.get_final('images')[0]['path'])

    def _update_product_options(self, item, site_product):
        for product_option in ['colors', 'patterns']:
            product_option_values = item.get_final(product_option)
            if product_option_values:
                for product_option_value in product_option_values:
                    # Option type name is singular
                    option_type = self.option_types.get(product_option[:-1])
                    if option_type:
                        option, created = self.site_option_model.objects.get_or_create(option_type=option_type, value=product_option_value)
                        if not site_product.options.filter(pk=option.pk).exists():
                            site_product.options.add(option)

    def _update_vendor_product(self, item, site_product):
        vendor = Vendor.objects.get(name=item.get_final('vendor'))
        vendor_product, _ = self.vendor_product_model.objects.get_or_create(product=site_product,
                                                                            vendor_id=vendor.vendor_id)
        vendor_product.buy_url = item.get_final('buy_url')
        vendor_product.original_price = item.get_final('regular_price') or '0.0'
        vendor_product.original_currency = item.get_final('currency')
        vendor_product.original_discount_price = item.get_final('discount_price')
        vendor_product.original_discount_currency = item.get_final('currency')
        vendor_product.availability = bool(item.get_final('in_stock', False))
        # XXX: price, currency and discount_price should not be used, WHY???
        #vendor_product.price = item.get_final('regular_price') or '0.0'
        #vendor_product.currency = item.get_final('currency')
        #vendor_product.discount_price = item.get_final('discount_price')
        vendor_product.save()

    def _find_site_product(self, item):
        """
        Find a product on the live site by slug or explicit mapping.
        """
        site_product_pk = item.get_site_product()
        if site_product_pk:
            try:
                return self.site_product_model.objects.get(pk=site_product_pk)
            except self.site_product_model.DoesNotExist:
                item.set_site_product(None)

        slug = slugify('%s-%s' % (item.get_final('brand'), item.get_final('name')))
        try:
            return self.site_product_model.objects.get(slug=slug)
        except self.site_product_model.DoesNotExist:
            pass
