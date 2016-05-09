from django.core.management.base import BaseCommand
from apparelrow.statistics.models import ProductStat

from progressbar import ProgressBar, Percentage, Bar


class Command(BaseCommand):
    args = ''
    help = 'Update referer for ProductStat instances, so it will only include HTTP referer link and not any other'

    def handle(self, *args, **options):
        product_stats = ProductStat.objects.all()
        count = 0

        # Initialize progress bar
        pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=len(product_stats)).start()

        for row in product_stats:
            if row.referer:
                referer_array = row.referer.split('\n')

                if len(referer_array) > 0:
                    row.referer = referer_array[0]
                    row.save()
                pbar.update(count)
                count += 1

        pbar.finish()