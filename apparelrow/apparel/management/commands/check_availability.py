import pysolr

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models.signals import post_save
from django.core.mail import mail_admins

from apparelrow.apparel.models import Product
from apparelrow.apparel.search import ApparelSearch

class Command(BaseCommand):
    args = ''
    # This is probably not correct, it seems to check inconsistencies between the database and solr index rather than checking for missing images..
    help = 'Finds all product with a missing image (takes awhile)'
    option_list = BaseCommand.option_list + (
            make_option('--email',
                action='store_true',
                dest='email',
                default=False,
                help='Send a report via email'),
            )

    def log(self, message):
        if self.email:
            self.log_buffer.append(message)
        else:
            print message

    def finish(self):
        if self.email:
            mail_admins('ApparelRow availability report', '\n'.join(self.log_buffer))

    def handle(self, *args, **options):
        counter = 0
        bad_counter = 0
        solr_connection = pysolr.Solr(settings.SOLR_URL)

        self.email = False
        if options['email']:
            self.email = True
            self.log_buffer = []

        for product_id in Product.objects.values_list('pk', flat=True).iterator():
            if counter % 5000 == 0 and counter > 0:
                print 'Checked %s products' % (counter,)

            result = ApparelSearch('id:apparel.product.%s AND availability:true AND published:true' % product_id, connection=solr_connection)
            if len(result):
                product = Product.objects.get(pk=product_id)
                if product.published == False:
                    self.log('Product %s is unpublished, but available in search' % (product_id,))
                    post_save.send(sender=product.__class__, instance=product)
                    bad_counter = bad_counter + 1
                elif product.availability == 0:
                    self.log('Product %s is unavailable, but available in search' % (product_id,))
                    post_save.send(sender=product.__class__, instance=product)
                    bad_counter = bad_counter + 1

            counter = counter + 1

        self.log('Updated search index for %s of %s products' % (bad_counter, counter))
        self.finish()
