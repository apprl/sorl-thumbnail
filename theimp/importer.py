import logging

from django.conf import settings
from django.db.models.loading import get_model

from hotqueue import HotQueue


logger = logging.getLogger(__name__)


class Importer(object):

    def run(self):
        self.site_queue = HotQueue(settings.THEIMP_QUEUE_SITE,
                                   host=settings.THEIMP_REDIS_HOST,
                                   port=settings.THEIMP_REDIS_PORT,
                                   db=settings.THEIMP_REDIS_DB)
        for product_id, valid in self.site_queue.consume():
            try:
                product = get_model('theimp', 'Product').objects.get(pk=product_id)
            except get_model('theimp', 'Product').DoesNotExist as e:
                logger.exception('Could not load product with id %s' % (product_id,))

            if valid:
                self.add_or_update(product)
            else:
                self.hide_product(product)

    def add_or_update(self, product):
        site_product = self.match(product)
        if not site_product:
            # TODO: add to database and solr
            pass
        else:
            # TODO: update database and solr
            pass

    def hide_product(self, product):
        site_product = self.match(product)
        if site_product:
            # TODO: set availability to false and update solr
            pass

    def match(self, product):
        # TODO: try to match theimp.Product to an apparel.Product

        return None
