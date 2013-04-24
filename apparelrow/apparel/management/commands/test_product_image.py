from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.files import storage

from apparelrow.apparel.models import Product, LookComponent, ProductLike


class Command(BaseCommand):
    args = ''
    help = ''
    option_list = BaseCommand.option_list

    def handle(self, *args, **options):
        counter = bad_counter = bad_size_counter = 0
        for product in Product.published_objects.values('pk', 'product_image').order_by('pk').iterator():
            if counter % 2000 == 0 and counter > 0:
                print 'Verified %s products - Bad: %s - Size: %s' % (counter, bad_counter, bad_size_counter)

            fail = False
            if not storage.default_storage.exists(product['product_image']):
                bad_counter += 1
                fail = True
            elif storage.default_storage.size(product['product_image']) <= 0:
                bad_size_counter += 1
                fail = True

            if fail:
                lc = LookComponent.objects.filter(product=product['pk']).exists()
                ll = ProductLike.objects.filter(product=product['pk']).exists()
                if lc or ll:
                    print 'exists in productlike or lookcomponent', product['pk']

                p = Product.objects.get(pk=product['pk'])
                p.published = False
                p.product_image = ''
                p.save()

            counter += 1

        print '%s bad of %s' % (bad_counter, counter)
        print '%s bad size of %s' % (bad_size_counter, counter)
