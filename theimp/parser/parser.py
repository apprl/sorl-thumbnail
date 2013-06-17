import json
import logging

from django.db.models.loading import get_model

logger = logging.getLogger(__name__)


class Parser:

    def __init__(self):
        self.modules = [
            'theimp.parser.modules.brand_mapper.BrandMapper',
            'theimp.parser.modules.category_mapper.CategoryMapper',
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
        print self.loaded_modules

        # TODO: read from queue
        for product in get_model('theimp', 'Product').objects.iterator():
            item = json.loads(product.json)

            # TODO: produce a new layer in the json for parsed values (so we
            # store both the imported and parsed value)

            for module in self.loaded_modules:
                item = module(item)

            # TODO: save json to database again

            # TODO: run validator (check for manual validation also)

            # TODO: add to out-to-site queue
