import datetime
import logging

from apparelrow.dashboard.models import Sale

from django.core.management.base import BaseCommand

logger = logging.getLogger('dashboard')


class Command(BaseCommand):
    def handle(self, *args, **options):
        for sale in Sale.objects.\
                filter(type=Sale.COST_PER_CLICK, status=Sale.PENDING):
            if sale.created < datetime.datetime.now() - datetime.timedelta(days=30):
                    sale.status = Sale.CONFIRMED
                    sale.save()
                    logger.info("Sale %s has been confirmed" % sale.id)
