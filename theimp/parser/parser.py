import logging
import json
import decimal

from django.db.models.loading import get_model

logger = logging.getLogger(__name__)


class Parser:

    required_fields = ['name', 'description', 'brand', 'category', 'gender', 'images',
                       'currency', 'regular_price', 'buy_url']
    required_layers = ['scraped', 'parsed', 'final']
    gender_values = ['M', 'W', 'U']

    def __init__(self):
        self.modules = [
            'theimp.parser.modules.build_buy_url.BuildBuyURL',
            'theimp.parser.modules.brand.BrandMapper',
            'theimp.parser.modules.category.CategoryMapper',
            'theimp.parser.modules.gender.GenderMapper',
            'theimp.parser.modules.price.Price',
        ]
        self.load_modules()
        self.load_vendors()

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

    def load_vendors(self):
        """
        Load vendors.
        """
        self.vendors = {}
        for vendor in get_model('theimp', 'Vendor').objects.iterator():
            self.vendors[vendor.name] = vendor

    def run(self):
        """
        Run parser.
        """
        # TODO: read from queue instead of database
        for product in get_model('theimp', 'Product').objects.iterator():
            logger.info('Parse key %s' % (product.key,))

            try:
                item = json.loads(product.json)
            except (ValueError, AttributeError) as e:
                logger.exception('Could not load JSON')
                continue

            if not self.validate_layers(item):
                logger.error('Invalid layer specification')
                continue

            vendor = self.validate_vendor(product, item)

            item = self.setup(item)

            scraped_item = item['scraped']
            parsed_item = item['parsed']
            for module in self.loaded_modules:
                parsed_item = module(scraped_item, parsed_item, product.vendor_id)
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
                logger.info('Successful validation moving to queue')
                # TODO: add to out-to-site queue
            else:
                logger.info('Unsuccessful validation, try to hide the product on site')
                # TODO: add to "remove-availability" queue

    def validate_layers(self, item):
        for layer in self.required_layers:
            if layer not in item:
                return False

        return True

    def validate_vendor(self, product, item):
        scraped_vendor = item['scraped']['vendor']

        if scraped_vendor not in self.vendors:
            vendor, _ = Vendor.objects.get_or_create(name=scraped_vendor)
            self.vendors[scraped_vendor] = vendor
            logger.warning('Created vendor %s during parse step.' % (scraped_vendor,))

        if product.vendor_id != self.vendors[scraped_vendor].pk:
            product.vendor_id = self.vendors[scraped_vendor].pk
            product.save()
            logger.warning('Update product vendor to %s' % (scraped_vendor,))

        return self.vendors[scraped_vendor]

    def setup(self, item):
        # TODO: might move this / parts of it to a module
        item['parsed']['name'] = item['scraped']['name']
        item['parsed']['description'] = item['scraped']['description']
        item['parsed']['vendor'] = item['scraped']['vendor']
        item['parsed']['affiliate'] = item['scraped']['affiliate']
        # TODO: how should we handle images? we need to upload to s3 somehow
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

            if not item['parsed'][field]:
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
