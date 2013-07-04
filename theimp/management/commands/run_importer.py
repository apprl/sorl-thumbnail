from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hotqueue import HotQueue


class Command(BaseCommand):
    args = ''
    help = 'Importer worker'

    def handle(self, *args, **options):
        # TODO: run as a daemon?
        self.site_queue = HotQueue(settings.THEIMP_QUEUE_SITE,
                                   host=settings.THEIMP_REDIS_HOST,
                                   port=settings.THEIMP_REDIS_PORT,
                                   db=settings.THEIMP_REDIS_DB)
        for product_id, valid in self.site_queue.consume():
            # TODO: here we should add the product to the site or if not valid
            # hide it from shop etc
            print product_id, valid
