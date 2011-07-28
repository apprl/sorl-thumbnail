from django.core.management.base import BaseCommand, CommandError

from apparelrow.apparel.models import Product, ProductLike, Wardrobe
from apparelrow.statistics.models import ProductClick 

class Command(BaseCommand):
    args = ''
    help = 'Updates popularity for all products (takes awhile)'

    def handle(self, *args, **options):
        for product in Product.objects.filter(published=True):
            product_click_count = 0
            try:
                product_click_count = ProductClick.objects.get(product=product).click_count
            except ProductClick.DoesNotExist:
                pass
            wardrobe_count = Wardrobe.objects.filter(products=product).count()
            like_count = ProductLike.objects.filter(product=product, active=True).count()

            product.popularity = like_count + wardrobe_count + 3 * product_click_count
            product.save()
