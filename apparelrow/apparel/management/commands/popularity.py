import datetime
import decimal
import logging

from django.core.management.base import BaseCommand, CommandError

from apparel.models import Product, ProductLike
from statistics.models import ProductClick

logger = logging.getLogger('apparel.management')

def batch_qs(qs, batch_size=1000):
    """
    Returns a (start, end, total, queryset) tuple for each batch in the given
    queryset.

    Usage:
        # Make sure to order your querset
        article_qs = Article.objects.order_by('id')
        for start, end, total, qs in batch_qs(article_qs):
            print "Now processing %s - %s of %s" % (start + 1, end, total)
            for article in qs:
                print article.body
    """
    total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield (start, end, total, qs[start:end])

ZERO = decimal.Decimal(0)

class Command(BaseCommand):
    args = ''
    help = 'Updates popularity for all products (takes awhile)'

    def handle(self, *args, **options):
        for start, end, total, query_set in batch_qs(Product.valid_objects.all(), batch_size=100):
            for product in query_set:
                product_click_count = 0
                try:
                    product_click_count = ProductClick.objects.get(product=product).click_count
                except ProductClick.MultipleObjectsReturned:
                    product_click_count = ProductClick.objects.filter(product=product)[:1][0].click_count
                    logger.warning('Duplicate item found in ProductClick: %s' % (product.product_name,))
                except ProductClick.DoesNotExist:
                    pass
                two_weeks_behind = datetime.datetime.now() - datetime.timedelta(weeks=2)
                like_count = ProductLike.objects.filter(
                        product=product,
                        active=True,
                        created__gte=two_weeks_behind).count()
                votes = like_count + 1 * product_click_count
                timedelta = datetime.datetime.now() - product.date_added
                item_half_hour_age =  (timedelta.days * 86400 + timedelta.seconds) / 7200
                if item_half_hour_age > 0:
                    product.popularity = str(votes / pow(item_half_hour_age, 1.53))
                    product.save()
                elif popularity > ZERO:
                    product.popularity = ZERO
                    product.save()
