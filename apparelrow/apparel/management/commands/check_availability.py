import pysolr

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models.signals import post_save

from apparelrow.apparel.models import Product, VendorProduct
from apparelrow.search import ApparelSearch

class Command(BaseCommand):
    args = ''
    help = 'Finds all product with a missing image (takes awhile)'

    def handle(self, *args, **options):
        counter = 0
        bad_counter = 0
        solr_connection = pysolr.Solr(getattr(settings, 'HAYSTACK_SOLR_URL', 'http://127.0.0.1:8983/solr/'))

        for product_id, published in Product.objects.values_list('pk', 'published').iterator():
            if counter % 5000 == 0 and counter > 0:
                print 'Checked %s products' % (counter,)

            result = ApparelSearch('id:apparel.product.%s AND availability:true' % product_id, connection=solr_connection)
            if len(result):
                availability = VendorProduct.objects.filter(product=product_id).order_by('price').values_list('availability', flat=True)[0]
                if published == False:
                    print 'Product %s is unpublished, but available in search' % (product_id,)
                    product = Product.objects.get(pk=product_id)
                    post_save.send(sender=product.__class__, instance=product)
                    bad_counter = bad_counter + 1
                elif availability == 0:
                    print 'Product %s is unavailable, but not in search' % (product_id,)
                    product = Product.objects.get(pk=product_id)
                    post_save.send(sender=product.__class__, instance=product)
                    bad_counter = bad_counter + 1

            counter = counter + 1

        print 'Updated search index for %s of %s products' % (bad_counter, counter)
