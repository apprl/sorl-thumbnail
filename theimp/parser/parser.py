import json
import logging

from django.db.models.loading import get_model

logger = logging.getLogger(__name__)


class Parser:

    required_fields = ['name', 'description', 'brand', 'category', 'gender']
    required_layers = ['scraped', 'parsed', 'final']
    gender_values = ['M', 'W', 'U']

    def __init__(self):
        self.modules = [
            #'theimp.parser.modules.build_buy_url.BuildBuyURL',
            'theimp.parser.modules.brand_mapper.BrandMapper',
            'theimp.parser.modules.category_mapper.CategoryMapper',
            'theimp.parser.modules.gender_mapper.GenderMapper',
        ]
        self.load_modules()

    def load_modules(self):
        self.loaded_modules = []
        for module in self.modules:
            module_path, module_name = module.rsplit('.', 1)
            try:
                loaded_module = __import__(module_path, fromlist=[module_name])
                self.loaded_modules.append(getattr(loaded_module, module_name)(self))
            except (ImportError, AttributeError):
                logger.exception('Could not load module')

    def run(self):
        # TODO: read from queue instead of database
        for product in get_model('theimp', 'Product').objects.iterator():
            try:
                item = json.loads(product.json)
            except (ValueError, AttributeError) as e:
                logger.exception('Could not load JSON for key: %s' % (product.key,))
                continue

            if not self.validate_layers(item):
                logger.error('Invalid layer specification in JSON for key: %s' % (product.key,))
                continue

            scraped_item = item['scraped']
            parsed_item = item['parsed']
            for module in self.loaded_modules:
                parsed_item = module(scraped_item, parsed_item, product.vendor_id)
            item['parsed'] = parsed_item

            validated = self.validate(product.key, item)

            product.is_auto_validated = validated
            product.json = json.dumps(item)
            product.save()

            # TODO: move parsed to final (?)
            # TODO: add to out-to-site queue

    def validate_layers(self, item):
        for layer in self.required_layers:
            if layer not in item:
                return False

        return True

    def validate(self, key, item):
        """
        Required fields: name, description, brand, category, gender
        """
        for field in self.required_fields:
            if field not in item['parsed']:
                logger.error('Missing required field %s for key: %s' % (field, key))
                return False

            if not item['parsed'][field]:
                return False

        if item['parsed']['gender'] not in self.gender_values:
            logger.error('Invalid gender value for key: %s' % (key,))
            return False

        # TODO: check that required fields are set, check that values seem correct

        # TODO: if a few interesting values changed we should mark is_manual_validated as invalid

        return True
