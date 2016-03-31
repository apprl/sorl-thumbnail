from django.core.management.base import BaseCommand
from apparelrow.statistics.models import ProductStat


class Command(BaseCommand):
    args = ''
    help = 'Update referer for ProductStat instances, so it will only include HTTP referer link and not any other'

    def handle(self, *args, **options):
        product_stats = ProductStat.objects.all()

        for row in product_stats:
            referer_array = row.referer.split('\n')

            if len(referer_array) > 0:
                row.referer = referer_array[0]
                row.save()