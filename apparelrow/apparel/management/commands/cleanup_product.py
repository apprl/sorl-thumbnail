import datetime
from optparse import make_option

from django.core.management.base import BaseCommand

from apparelrow.apparel.models import Product, ProductLike, LookComponent


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        deleted_count = 0

        seven_days_ago = datetime.datetime.today() - datetime.timedelta(days=7)

        product_count = Product.objects.filter(published=False, date_published__isnull=True, modified__lte=seven_days_ago).count()
        print 'About to check {} products'.format(product_count)

        for product_id in Product.objects.filter(published=False, date_published__isnull=True, modified__lte=seven_days_ago).values_list('pk', flat=True):
            if ProductLike.objects.filter(product=product_id).count() == 0 and LookComponent.objects.filter(product=product_id).count() == 0:
                product = Product.objects.get(pk=product_id)
                product.delete()
                deleted_count += 1
            else:
                print 'Could not delete {}'.format(product_id)

        print 'Deleted {0} products'.format(deleted_count)
