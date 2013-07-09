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
                continue

            try:
                if valid:
                    self.add_or_update(product)
                else:
                    self.hide_product(product)
            except Exception as e:
                logger.exeception('Could not update or hide product: %s' % (product,))
            else:
                product.save()

    def add_or_update(self, product):
        logger.debug('Add or update product called with argument: %s' % (product,))

        site_product = self.match(product)
        if not site_product:
            # TODO: add to database and solr
            logger.info('Add product to site: %s' % (product,))
        else:
            # TODO: update database and solr
            logger.info('Update site product %s with %s' % (site_product, product,))

    def hide_product(self, product):
        logger.debug('Hide product called with argument: %s' % (product,))

        site_product = self.match(product)
        if site_product:
            # TODO: set availability to false and update solr
            logger.info('Hide site product: %s' % (site_product,))

    def match(self, product):
        # TODO: try to match theimp.Product to an apparel.Product

        return None
