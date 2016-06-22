from django.core.management.base import BaseCommand
from apparelrow.statistics.models import ProductStat

from progressbar import ProgressBar, Percentage, Bar


class Command(BaseCommand):
    args = ''
    help = 'Update referer for ProductStat instances, so it will only include HTTP referer link and not any other'

    def handle(self, *args, **options):
        #product_stats = ProductStat.objects.all()
        steps = 10000
        position = 0
        for i in range(steps, 2000000, steps):
            products = ProductStat.objects.all()[position:i]
            if not products:
                print "No productstats to handle"
                return
            pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=products.count()).start()
            for index, row in enumerate(products):
                pbar.update(index)
                if row.referer:
                    referer_array = row.referer.split('\n')

                    if len(referer_array) > 0:
                        row.referer = referer_array[0]
                        row.save()
            pbar.finish()
            position = i
