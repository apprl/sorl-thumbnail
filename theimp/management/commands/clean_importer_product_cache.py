# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

from theimp.models import Product as ImpProduct
from optparse import make_option
from django.core.management.base import BaseCommand
from django.core.cache import get_cache
from apparelrow.apparel.models import Product
from progressbar import ProgressBar, Percentage, Bar


class Command(BaseCommand):
    args = ''
    help = 'Command for cleaning the '
    option_list = BaseCommand.option_list + (
        make_option('--impvendor_id',
                    action='store',
                    dest='impvendor_id',
                    default=None,
        ),
        make_option('--vendor_id',
                    action='store',
                    dest='vendor_id',
                    default=None,
        )
    )

    imported_cache_key = "imported_{id}"
    scraped_cache_key = "scraped_{id}"

    def handle(self, *args, **options):
        impvendor_id = options.get('impvendor_id')
        vendor_id = options.get('vendor_id')
        cache = None
        try:
            cache = get_cache("importer")
        except:
            print "Failed to load importer cache, quitting."
            return

        if vendor_id:
            try:
                pbar = ProgressBar(widgets=[Percentage(), Bar()],
                               maxval=Product.objects.filter(vendors__id__in=[vendor_id]).count()).start()
                for index, p in enumerate(
                        Product.objects.filter(vendors__id__in=[vendor_id]).values_list("id", flat=True).iterator()):
                    # print "Removing importcache for product {id}.".format(id=p)
                    pbar.update(index)
                    cache.delete(self.imported_cache_key.format(id=p))
                pbar.finish()
            except ZeroDivisionError:
                print "No products available for vendor"
        try:
            if impvendor_id:
                pbar = ProgressBar(widgets=[Percentage(), Bar()],
                                   maxval=ImpProduct.objects.filter(vendor_id__in=[impvendor_id]).count()).start()
                for index, p in enumerate(
                        ImpProduct.objects.filter(vendor_id__in=[impvendor_id]).values_list("id", flat=True).iterator()):
                    # print "Remove scrapecache for imp product {id}.".format(id=p)
                    pbar.update(index)
                    cache.delete(self.scraped_cache_key.format(id=p))
                pbar.finish()
        except ZeroDivisionError:
            print "No products available for imp vendor"
