from django.core.management.base import BaseCommand, CommandError
from django.core.files import storage

from apparelrow.apparel.models import Product

class Command(BaseCommand):
    args = ''
    help = 'Finds all product with a missing image (takes awhile)'

    def handle(self, *args, **options):
        counter = 0
        for product in Product.objects.all():
            if counter % 5000 == 0 and counter > 0:
                print 'Checked %s products' % (counter,)

            if not storage.default_storage.exists(product.product_image):
                print 'Product: %s\n - id: %s\n - image: %s\n - vendor: %s' % (product, product.id, product.product_image, product.vendors.all())

            counter = counter + 1

        print 'Checked %s products' % (counter,)
