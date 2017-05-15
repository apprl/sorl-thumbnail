from django.core.management.base import BaseCommand
from apparelrow.statistics.models import ProductStat
import logging
import sys
import os
import optparse

from progressbar import ProgressBar, Percentage, Bar

log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = ''
    help = 'Update referer for ProductStat instances, so it will only include HTTP referer link and not any other'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--skip_progress',
                             action='store',
                             dest='skip_progress',
                             help='Add switch to turn off progress bar reporting',
                             default=False,
                             ),
    )

    def handle(self, *args, **options):
        #product_stats = ProductStat.objects.all()
        steps = 10000
        position = 0
        skip_progress = options.get('skip_progress')
        for i in range(steps, 2000000, steps):
            products = ProductStat.objects.all()[position:i]
            if not products:
                log.info("No productstats to handle")
                return
            fd = open(os.devnull, 'w') if skip_progress else sys.stdout
            pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=products.count(), fd=fd).start()
            for index, row in enumerate(products):
                pbar.update(index)
                if row.referer:
                    referer_array = row.referer.split('\n')

                    if len(referer_array) > 0:
                        row.referer = referer_array[0]
                        row.save()
            pbar.finish()
            position = i
