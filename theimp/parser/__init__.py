from django.core.cache import get_cache
import logging
import json
import decimal
from pprint import pformat

from django.conf import settings
from django.db.models.loading import get_model
from django.utils import timezone
from django.utils.html import strip_tags

from theimp.utils import ProductItem, get_product_hash

logger = logging.getLogger(__name__)
cache = get_cache("importer")


class Parser(object):

    required_fields = ['sku', 'name', 'description', 'brand', 'category', 'gender', 'images',
                       'currency', 'regular_price', 'url', 'vendor']
    gender_values = ['M', 'W', 'U']
    final_cache_key = "finalized_{id}"

    def __init__(self):
        self.modules = [
            'theimp.parser.modules.build_buy_url.BuildBuyURL',
            'theimp.parser.modules.brand.BrandMapper',
            'theimp.parser.modules.category.CategoryMapper',
            'theimp.parser.modules.gender.GenderMapper',
            'theimp.parser.modules.price.Price',
            'theimp.parser.modules.option.OptionMapper',
        ]
        self.load_modules()

    def load_modules(self):
        """
        Load modules used by parser.
        """
        self.loaded_modules = []
        for module in self.modules:
            module_path, module_name = module.rsplit('.', 1)
            try:
                loaded_module = __import__(module_path, fromlist=[module_name])
                self.loaded_modules.append(getattr(loaded_module, module_name)(self))
            except (ImportError, AttributeError):
                logger.exception('Could not load module')

    def parse(self, product):
        """
        Take the scraped data and filter it through the loaded_modules after it has been prepared with initial_parse
        :param product:
        :return:
        """
        if not product:
            logger.error('Could not parse invalid product')
            return

        logger.info('Parse product id %s' % (product.pk,))

        # Load product json and validate initial specification
        item = ProductItem(product)
        if not item.validate_keys():
            logger.error('Invalid product json data specification')
            return

        # Pre validate vendor for use in parser modules
        vendor = self._validate_vendor(item.get_scraped('vendor'))
        if not vendor:
            logger.error('Invalid vendor in product json data: %s' % (item.get_scraped('vendor'),))
            return

        item = self.initial_parse(item)

        scraped_item = item.data[ProductItem.KEY_SCRAPED]
        parsed_item = item.data[ProductItem.KEY_PARSED]
        for module in self.loaded_modules:
            parsed_item = module(scraped_item, parsed_item, vendor, product=product)
        item.data[ProductItem.KEY_PARSED] = parsed_item

        validated = self.validate(item, vendor)
        item = self.finalize(item, validated)

        final_hash = get_product_hash(item.data[ProductItem.KEY_FINAL])
        previous_hash = cache.get(self.final_cache_key.format(id=product.id))

        product.is_validated = validated if not product.is_dropped else False
        product.parsed_date = timezone.now()

        # Only save the new data if it has changed. Saves time.
        if not previous_hash == final_hash:
            cache.set(self.final_cache_key.format(id=product.id), final_hash, 3600*6)
            product.json = json.dumps(item.data)
            product.save()
        else:
            product.save(update_fields=['is_validated', 'parsed_date'])

        return validated

    def initial_parse(self, item):
        """
        Inital parse consists of migrating key fields from scraped (item) to parsed.
        :param item: ProductItem object containing three (four if counting manual input) versions of the product attributes
        :return:
        """
        for key in ['name', 'description']:
            value = item.get_scraped(key)
            if value:
                item.data[ProductItem.KEY_PARSED][key] = strip_tags(value).strip()

        for key in ['sku', 'vendor', 'affiliate', 'in_stock', 'images']:
            value = item.get_scraped(key)
            if value is not None:
                item.data[ProductItem.KEY_PARSED][key] = value

        stock = item.get_scraped('stock')
        if stock:
            try:
                item.data[ProductItem.KEY_PARSED]['stock'] = int(stock)
            except (TypeError, ValueError):
                pass

        return item


    def finalize(self, item, validated):
        """
        Moves all the parsed fields into column final, which is later used for importing into apparel.Product
        :param item:
        :param validated:
        :return: ProductItem with updated Final
        """
        item.data[ProductItem.KEY_FINAL] = {}
        if validated:
            for key in item.data[ProductItem.KEY_PARSED].keys():
                if (key == 'brand_id' or key == 'brand') and ProductItem.KEY_MANUAL in item.data and item.data[ProductItem.KEY_MANUAL].get('brand',None):
                    item.data[ProductItem.KEY_FINAL]['brand'] = item.product.brand_mapping.mapped_brand.name
                    item.data[ProductItem.KEY_FINAL]['brand_id'] = item.product.brand_mapping.mapped_brand.pk
                elif (key == 'category_id' or key == 'category') and ProductItem.KEY_MANUAL in item.data and item.data[ProductItem.KEY_MANUAL].get('category',None):
                    item.data[ProductItem.KEY_FINAL]['category'] = item.product.category_mapping.mapped_category.name
                    item.data[ProductItem.KEY_FINAL]['category_id'] = item.product.category_mapping.mapped_category.pk
                else:
                    item.data[ProductItem.KEY_FINAL][key] = item.get_parsed(key)
        return item

    def _validate_vendor(self, vendor_name):
        try:
            return get_model('theimp', 'Vendor').objects.get(name=vendor_name)
        except get_model('theimp', 'Vendor').DoesNotExist:
            logger.warning('Could not validate vendor: %s' % (vendor_name,))

        return None

    def validate(self, item, vendor):
        for field in self.required_fields:
            if not item.get_parsed(field):
                logger.warning('Missing required field %s' % (field,))
                logger.debug('Data:\n%s' % (pformat(item.data),))
                return False

        # Validate and setup manual brand if needed (ugly hack)
        if ProductItem.KEY_MANUAL in item.data and item.data[ProductItem.KEY_MANUAL].get('brand',None):
            manual_brand_id = item.data[ProductItem.KEY_MANUAL]['brand']
            try:
                brand = get_model('apparel', 'Brand').objects.get(pk=int(manual_brand_id))
                mapping, _ = get_model('theimp', 'BrandMapping').objects.get_or_create(
                    brand='%s-manual' % (manual_brand_id,),
                    vendor_id=vendor.pk,
                    mapped_brand=brand)

                item.product.brand_mapping = mapping
                item.product.save()
            except Exception:
                logger.exception('Invalid manual brand id %s' % (manual_brand_id,))
                return False

        # Validate and setup manual category if needed (ugly hack)
        if ProductItem.KEY_MANUAL in item.data and item.data[ProductItem.KEY_MANUAL].get('category',None):
            manual_category_id = item.data[ProductItem.KEY_MANUAL]['category']
            try:
                category = get_model('apparel', 'Category').objects.get(pk=int(manual_category_id))
                mapping, _ = get_model('theimp', 'CategoryMapping').objects.get_or_create(
                    category='%s-manual' % (manual_category_id,),
                    vendor_id=vendor.pk,
                    mapped_category=category)

                item.product.category_mapping = mapping
                item.product.save()
            except Exception:
                logger.exception('Invalid manual category id %s' % (manual_category_id,))
                return False

        # Validate gender value
        if item.get_parsed('gender') not in self.gender_values:
            logger.warning('Invalid gender value: %s' % (item.get_parsed('gender'),))
            logger.debug('Data:\n%s' % (pformat(item.data),))
            return False

        # Validate currency
        # TODO: should validate against our imported currencies
        if len(item.get_parsed('currency')) != 3:
            logger.warning('Invalid currency value: %s' % (item.get_parsed('currency'),))
            logger.debug('Data:\n%s' % (pformat(item.data),))
            return False

        # Validate regular and discount price
        # TODO: how?

        # Validate vendor
        vendor = self._validate_vendor(item.get_parsed('vendor'))
        if not vendor.vendor_id:
            logger.warning('Vendor has no mapping: %s' % (item.get_parsed('vendor'),))
            logger.debug('Data:\n%s' % (pformat(item.data),))
            return False

        return True
