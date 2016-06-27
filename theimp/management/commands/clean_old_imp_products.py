# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

from theimp.models import Product as ImpProduct
from optparse import make_option
from django.core.management.base import BaseCommand
from progressbar import ProgressBar, Percentage, Bar
import datetime
from datetime import timedelta

class Command(BaseCommand):
    args = ''
    help = 'Update referer for ProductStat instances, so it will only include HTTP referer link and not any other'
    option_list = BaseCommand.option_list + (
            make_option('--vendor',
            action='store',
            dest='vendor',
            default=None,
        ),
        make_option('--offset',
            action='store',
            dest='offset',
            help='Select the amount of days to go back',
            default=550,
        ),
        make_option('--y',
            action='store_true',
            dest='input',
            help='No input needed',
            default=False,
        )
    )

    def handle(self, *args, **options):
        offset = int(options.get('offset'))

        purge_date = datetime.date.today() - timedelta(days=offset)
        total_products = ImpProduct.objects.filter(modified__lt=purge_date).count()

        input_verified = options.get("input")

        if not input_verified:
            prompt = "Will remove all scraped products not modified since {}: {} units. Are you sure? [Y/n]".format(purge_date, total_products)
            input_verified = bool(raw_input(prompt) == "Y")

        if input_verified:
            print ImpProduct.objects.filter(modified__lt=purge_date).delete()
        else:
            print "Canceling purge"
