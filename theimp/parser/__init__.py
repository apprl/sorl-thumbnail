import logging
import json
import decimal

from django.conf import settings
from django.db.models.loading import get_model
from django.utils.html import strip_tags

from hotqueue import HotQueue

from theimp.utils import load_product_json


logger = logging.getLogger(__name__)


class Parser(object):

    required_fields = ['name', 'description', 'brand', 'category', 'gender', 'images',
                       'currency', 'regular_price', 'buy_url', 'vendor_id']
    required_field_values = ['name', 'brand', 'category', 'gender', 'images',
                             'currency', 'regular_price', 'buy_url', 'vendor_id']
    required_layers = ['scraped', 'parsed', 'final']
    gender_values = ['M', 'W', 'U']

    def __init__(self, parse_queue=None, site_queue=None):
        self.modules = [
            'theimp.parser.modules.build_buy_url.BuildBuyURL',
            'theimp.parser.modules.brand.BrandMapper',
            'theimp.parser.modules.category.CategoryMapper',
            'theimp.parser.modules.gender.GenderMapper',
            'theimp.parser.modules.price.Price',
        ]
        self.load_modules()

        if not parse_queue:
            self.parse_queue = parse_queue_class(settings.THEIMP_QUEUE_PARSE,
                                                 host=settings.THEIMP_REDIS_HOST,
                                                 port=settings.THEIMP_REDIS_PORT,
                                                 db=settings.THEIMP_REDIS_DB)
        else:
            self.parse_queue = parse_queue

        if not site_queue:
            self.site_queue = site_queue_class(settings.THEIMP_QUEUE_SITE,
                                               host=settings.THEIMP_REDIS_HOST,
                                               port=settings.THEIMP_REDIS_PORT,
                                               db=settings.THEIMP_REDIS_DB)
        else:
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

            # Load product json
            item = load_product_json(product)

            if not self.validate_layers(item):
                logger.error('Invalid layer specification')
                continue

            item, vendor = self.validate_vendor(product, item)
            if not vendor:
                continue

            item = self.initial_parse(item)

            scraped_item = item['scraped']
            parsed_item = item['parsed']
            for module in self.loaded_modules:
                parsed_item = module(scraped_item, parsed_item, vendor)
            item['parsed'] = parsed_item

            validated = self.validate(item)
            if validated:
                item['final'] = item['parsed']

            product.is_auto_validated = validated
            product.json = json.dumps(item)
            product.save()

            import pprint
            pprint.pprint(item)

            if validated:
                logger.info('Parsed product successful moving to site queue: (%s, %s)' % (product.pk, validated))
            else:
                logger.info('Parsed product unsuccessful moving to site queue: (%s, %s)' % (product.pk, validated))

            self.site_queue.put((product.pk, validated))

    def validate_layers(self, item):
        for layer in self.required_layers:
            if layer not in item:
                return False

        return True

    def validate_vendor(self, product, item):
        scraped_vendor = item['scraped']['vendor']
        try:
            vendor = get_model('theimp', 'Vendor').objects.get(name=scraped_vendor)
        except get_model('theimp', 'Vendor').DoesNotExist:
            logger.error('Could not find vendor for %s' % (scraped_vendor,))
            return item, None

        if vendor.vendor_id:
            item['scraped']['vendor_id'] = vendor.vendor_id
        else:
            item['scraped']['vendor_id'] = None

        return item, vendor

    def initial_parse(self, item):
        # TODO: might move this / parts of it to a module
        item['parsed']['name'] = strip_tags(item['scraped']['name']).strip()
        item['parsed']['description'] = strip_tags(item['scraped']['description']).strip()
        item['parsed']['vendor_id'] = item['scraped']['vendor_id']
        item['parsed']['affiliate'] = item['scraped']['affiliate']
        item['parsed']['in_stock'] = item['scraped']['in_stock']
        item['parsed']['images'] = item['scraped']['images']

        return item

    def validate(self, item):
        """
        Required fields:
            name, description, brand, category, gender, images, currency, price, buy_url
        """
        for field in self.required_fields:
            if field not in item['parsed']:
                logger.warning('Missing required field %s' % (field,))
                return False

        for field in self.required_field_values:
            if not item['parsed'][field]:
                logger.warning('Missing required field %s value' % (field,))
                return False

        # Validate gender value
        if item['parsed']['gender'] not in self.gender_values:
            logger.warning('Invalid gender value: %s' % (item['parsed']['gender'],))
            return False

        # Validate currency
        if len(item['parsed']['currency']) != 3:
            logger.warning('Invalid currency value: %s' % (item['parsed']['currency'],))
            return False

        # TODO: if a few interesting values changed we should mark is_manual_validated as invalid
        # TODO: if parsed is different from manual_validated created checksum
        # mark product as not manual_validated, auto validation still applies tho.

        return True
