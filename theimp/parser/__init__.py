import logging
import json
import decimal

from django.conf import settings
from django.db.models.loading import get_model
from django.utils.html import strip_tags

from hotqueue import HotQueue

from theimp.utils import ProductItem


logger = logging.getLogger(__name__)


class Parser(object):

    required_fields = ['name', 'description', 'brand', 'category', 'gender', 'images',
                       'currency', 'regular_price', 'buy_url', 'vendor_id']
    gender_values = ['M', 'W', 'U']

    def __init__(self, parse_queue=None, site_queue=None):
        self.modules = [
            'theimp.parser.modules.build_buy_url.BuildBuyURL',
            'theimp.parser.modules.brand.BrandMapper',
            'theimp.parser.modules.category.CategoryMapper',
            'theimp.parser.modules.gender.GenderMapper',
            'theimp.parser.modules.price.Price',
            'theimp.parser.modules.option.OptionMapper',
        ]
        self.load_modules()

        self.parse_queue = HotQueue(settings.THEIMP_QUEUE_PARSE,
                                    host=settings.THEIMP_REDIS_HOST,
                                    port=settings.THEIMP_REDIS_PORT,
                                    db=settings.THEIMP_REDIS_DB)
        if parse_queue:
            self.parse_queue = parse_queue

        self.site_queue = HotQueue(settings.THEIMP_QUEUE_SITE,
                                   host=settings.THEIMP_REDIS_HOST,
                                   port=settings.THEIMP_REDIS_PORT,
                                   db=settings.THEIMP_REDIS_DB)
        if site_queue:
            self.site_queue = site_queue

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

    def run(self):
        """
        Run parser.
        """
        for product_id in self.parse_queue.consume():
            try:
                product = get_model('theimp', 'Product').objects.get(pk=product_id)
            except get_model('theimp', 'Product').DoesNotExist as e:
                logger.exception('Could not load product with id %s' % (product_id,))
                continue

            logger.info('Begin parse for key: %s' % (product.key,))

            # Load product json and validate initial specification
            item = ProductItem(product)
            if not item.validate_keys():
                logger.error('Invalid product json data specification')
                continue

            # Validate vendor
            item, vendor = self.validate_vendor(item)
            if not vendor:
                logger.error('Invalid vendor in product json data')
                continue

            item = self.initial_parse(item)

            scraped_item = item.data[ProductItem.KEY_SCRAPED]
            parsed_item = item.data[ProductItem.KEY_PARSED]
            for module in self.loaded_modules:
                parsed_item = module(scraped_item, parsed_item, vendor)
            item.data[ProductItem.KEY_PARSED] = parsed_item

            validated = self.validate(item)
            if validated:
                for key in item.data[ProductItem.KEY_PARSED].keys():
                    item.data[ProductItem.KEY_FINAL][key] = item.get_parsed(key)

            product.is_auto_validated = validated
            product.json = json.dumps(item.data)
            product.save()

            import pprint
            pprint.pprint(item.data)

            if validated:
                logger.info('Parsed product successful moving to site queue: (%s, %s)' % (product.pk, validated))
            else:
                logger.info('Parsed product unsuccessful moving to site queue: (%s, %s)' % (product.pk, validated))

            self.site_queue.put((product.pk, validated))

    def validate_vendor(self, item):
        scraped_vendor = item.get_scraped('vendor')
        try:
            vendor = get_model('theimp', 'Vendor').objects.get(name=scraped_vendor)
        except get_model('theimp', 'Vendor').DoesNotExist:
            logger.error('Could not find vendor for %s' % (scraped_vendor,))
            return item, None

        if vendor.vendor_id:
            item.set_scraped('vendor_id', vendor.vendor_id)
        else:
            item.set_scraped('vendor_id', None)

        return item, vendor

    def initial_parse(self, item):
        for key in ['name', 'description']:
            value = item.get_scraped(key)
            if value:
                item.data[ProductItem.KEY_PARSED][key] = strip_tags(value).strip()

        for key in ['vendor_id', 'affiliate', 'in_stock', 'images']:
            value = item.get_scraped(key)
            if value:
                item.data[ProductItem.KEY_PARSED][key] = value

        stock = item.get_scraped('stock')
        if stock:
            try:
                item.data[ProductItem.KEY_PARSED]['stock'] = int(stock)
            except (TypeError, ValueError):
                pass

        return item

    def validate(self, item):
        for field in self.required_fields:
            if not item.get_parsed(field):
                logger.warning('Missing required field %s' % (field,))
                return False

        # Validate gender value
        if item.get_parsed('gender') not in self.gender_values:
            logger.warning('Invalid gender value: %s' % (item.get_parsed('gender'),))
            return False

        # Validate currency
        if len(item.get_parsed('currency')) != 3:
            logger.warning('Invalid currency value: %s' % (item.get_parsed('currency'),))
            return False

        return True
