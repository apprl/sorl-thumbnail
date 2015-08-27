from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.core.management import call_command
import logging

logger = logging.getLogger('dashboard')

class Command(BaseCommand):
    args = ''
    help = 'Update aggregated data from sales that might have changed through time'

    def handle(self, *args, **options):
        logger.info('Initiate update for aggregated data')
        cached_data = cache.get(settings.APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA)
        if cached_data:
            cached_list = cached_data.split(",")
            for item in cached_list:
                logger.info('Updating aggregated data for date %s' % item)
                call_command('collect_aggregated_data', date=item)
            cache.delete(settings.APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA)
        logger.info('Finished update for aggregated data')