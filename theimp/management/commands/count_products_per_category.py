import logging
import time
from django.core.management.base import BaseCommand
from django.db.models.loading import get_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    args = ''
    help = 'Counts products for every parsed category'

    def handle(self, *args, **options):
        logger.debug("Starting counting...")
        start = time.time()
        for category in self.get_category_mappings():
            products_counter = get_model('theimp', 'Product').objects.filter(category_mapping=category).count()
            if category.products_counter != products_counter:
                category.products_counter = products_counter
                category.save()
        end = time.time()
        logger.debug("Finishing on %s seconds"%(end - start))

    def get_category_mappings(self):
        category_mappings = get_model('theimp', 'CategoryMapping').objects.all()
        for category in category_mappings.iterator():
            yield category