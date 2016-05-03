from django.core.management.base import BaseCommand
from progressbar import ProgressBar, Percentage, Bar
from apparelrow.statistics.models import ProductStat


class Command(BaseCommand):
    args = ''
    help = 'Update referer for ProductStat instances, so it will only include HTTP referer link and not any other'

    def handle(self, *args, **options):
        #product_stats = ProductStat.objects.all()
        pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=ProductStat.objects.count()).start()
        for index, row in enumerate(ProductStat.objects.all()):
            pbar.update(index)
            if row.referer:
                referer_array = row.referer.split('\n')

                if len(referer_array) > 0:
                    row.referer = referer_array[0]
                    row.save()
        pbar.finish()