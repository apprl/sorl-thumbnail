import datetime

from django.core.management.base import BaseCommand, CommandError

from apparelrow.apparel.models import Product, ProductLike, Wardrobe
from apparelrow.statistics.models import ProductClick 

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

class Command(BaseCommand):
    args = ''
    help = 'Updates popularity for all products (takes awhile)'

    def handle(self, *args, **options):
        for start, end, total, query_set in batch_qs(Product.objects.filter(published=True, category__isnull=False, vendorproduct__isnull=False), batch_size=100):
            for product in query_set:
                product_click_count = 0
                try:
                    product_click_count = ProductClick.objects.get(product=product).click_count
                except ProductClick.DoesNotExist:
                    pass
                wardrobe_count = Wardrobe.objects.filter(products=product).count()
                like_count = ProductLike.objects.filter(product=product, active=True).count()
                votes = like_count + wardrobe_count + 3 * product_click_count
                timedelta = datetime.datetime.now() - product.date_added
                item_half_hour_age =  (timedelta.days * 86400 + timedelta.seconds) / 7200
                product.popularity = str(votes / pow(item_half_hour_age, 1.53))
                product.save()
