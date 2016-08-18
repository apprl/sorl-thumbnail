import pysolr

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models.signals import post_save
from django.core.mail import mail_admins
from datetime import datetime, date, timedelta

from apparelrow.apparel.models import Product as SiteProduct, Vendor as SiteVendor
from apparelrow.apparel.search import ApparelSearch
from theimp.models import Vendor as ImpVendor, Product as ImpProduct, CategoryMapping
from django.core.cache import get_cache

class Command(BaseCommand):
    args = ''
    cache_key = "vendor_product_history_{}"
    help = 'Checks for inconsistencies and checks how many products should be available, is available now, has been parsed without errors and so forth.'
    option_list = BaseCommand.option_list + (
            make_option('--email',
                action='store_true',
                dest='email',
                default=False,
                help='Send a report via email'),
           make_option('--vendorid',
                action='store',
                dest='vendor_id',
                default=None,
                help='Run job only for this vendor'),
            make_option('--verbose',
                action='store_true',
                dest='verbose',
                default=False,
                help='Show progress with progressbar.'),
            )

    def log(self, message):
        if self.email:
            self.log_buffer.append(message)
        else:
            print message

    def get_solr_products(self, vendor_id, solr_connection):
        result = ApparelSearch('django_ct:apparel.product AND store_id:{} AND availability:true AND published:true'.format(vendor_id), connection=solr_connection)
        return len(result)

    def finish(self):
        if self.email:
            mail_admins('ApparelRow scraping and mapping report', '\n'.join(self.log_buffer))

    def handle(self, *args, **options):
        counter = 0
        bad_counter = 0
        cache = get_cache("default")
        cache_time = 7*24*60*60
        modified_since = date.today() - timedelta(days=7)
        solr_connection = pysolr.Solr(settings.SOLR_URL)
        #verbose = options.get("verbose")

        self.email = False
        if options.get('email'):
            self.email = True
            self.log_buffer = []

        updated_since = datetime.today() - timedelta(days=90)
        # Loop through the different vendors, filter by id if provided
        vendor_filters = {"modified__gte": updated_since}
        if options.get("vendor_id"):
            vendor_filters.update({"id": options.get("vendor_id"), })

        for vendor in ImpVendor.objects.filter(**vendor_filters).iterator():
            # Check amount of products in total
            data = {"products_total": 0, "products_valid": 0, "categories_total": 0, "categories_mapped": 0,
                    "production_products_available": 0, "production_products_solr_published": 0}
            vendor_filter = {"vendor_id": vendor.id}
            total_products = ImpProduct.objects.filter(**vendor_filter) # add date filter also
            data.update({"products_not_valid_updated_last_week": total_products.filter(is_validated=False, modified__gt=modified_since).count(),
                         "products_valid_updated_last_week": total_products.filter(is_validated=True, modified__gt=modified_since).count()})
            total_categories = CategoryMapping.objects.filter(**vendor_filter)
            data.update({"categories_total": total_categories.count(),
                         "categories_mapped": total_categories.filter(mapped_category__isnull=False).count()})
            production_products = SiteProduct.objects.filter(vendors=vendor.vendor_id, availability=True)
            data.update({"production_products_available": production_products.count(),
                         "production_products_solr_published": self.get_solr_products(vendor.vendor_id, solr_connection)})
            previous_data = cache.get(self.cache_key.format(vendor.id))
            cache.set(self.cache_key.format(vendor.id), data, cache_time)
            keys = data.keys()
            # Minor infraction of DRY principle, non critical
            self.log("\n\n################# {} #################".format(vendor.name))
            if previous_data:
                for key in keys:
                    self.log("{}: {}/{} [{}]".format(key, data.get(key), previous_data.get(key, 0), abs(previous_data.get(key, 0) - data.get(key))))
            else:
                for key in keys:
                    self.log("{}: {}/{} [{}]".format(key, data.get(key), "-", "-"))

        #self.log('Updated search index for %s of %s products' % (bad_counter, counter))
        self.finish()
