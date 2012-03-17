from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.files import storage

from apparel.models import Product

class Command(BaseCommand):
    args = ''
    help = 'Finds all product with a missing image (takes awhile)'
    option_list = BaseCommand.option_list + (
        make_option('--remove',
            action='store_true',
            dest='remove_products',
            default=False,
            help='Remove products and everything related to them if they are missing product image on disk'
        ),
    )

    def handle(self, *args, **options):
        counter = 0
        bad_counter = 0
        for product in Product.objects.all():
            if counter % 5000 == 0 and counter > 0:
                print 'Checked %s products' % (counter,)

            if not storage.default_storage.exists(product.product_image):
                print 'Product: %s\n - id: %s\n - image: %s\n - vendor: %s' % (product, product.id, product.product_image, product.vendors.all(), product.default_vendor.availability)
                if product.default_vendor:
                    print ' - availability: %s' % (product.default_vendor.availability,)

                if options['remove_products']:
                    product.delete()

                bad_counter = bad_counter + 1

            counter = counter + 1

        print 'Checked %s products' % (counter,)

        if options['remove_products']:
            print 'Removed %s bad products' % (bad_counter,)
        else:
            print 'Found %s bad products' % (bad_counter,)
