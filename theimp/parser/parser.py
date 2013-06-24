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
            #'theimp.parser.modules.gender_mapper.GenderMapper',
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
                logger.error('Could not load JSON for key: %s' % (product.key,))

            if not self.pre_validate(product.key, item):
                logger.error('Invalid layers in JSON for key: %s' % (product.key,))
                break

            for module in self.loaded_modules:
                item = module(item)

            item, validated = self.validate(product.key, item)

            product.is_auto_validated = validated
            product.json = json.dumps(item)
            product.save()

            # TODO: move parsed to final (?)

            # TODO: add to out-to-site queue


    def pre_validate(self, key, item):
        for layer in self.required_layers:
            if layer not in item:
                logger.error('Missing layer %s in JSON for key: %s' % (layer, key))
                return False

        return True

    def validate(self, key, item):
        """
        Required fields: name, description, brand, category, gender
        """
        for field in self.required_fields:
            if field not in item['parsed']:
                logger.error('Missing required field %s for key: %s' % (field, key))

                return item, False

            if not item['parsed'][field]:
                return item, False

        if item['parsed']['gender'] not in self.gender_values:
            logger.error('Invalid gender value for key: %s' % (key,))

            return item, False

        # TODO: check that required fields are set, check that values seem correct

        # TODO: if a few interesting values changed we should mark is_manual_validated as invalid

        return item, True
