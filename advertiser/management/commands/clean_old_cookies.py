# -*- coding: utf-8 -*-
from advertiser.models import Cookie

__author__ = 'klaswikblad'

from theimp.models import Product as ImpProduct
from optparse import make_option
from django.core.management.base import BaseCommand
from progressbar import ProgressBar, Percentage, Bar
import datetime
from datetime import timedelta

class Command(BaseCommand):
    args = ''
    help = 'Remove older cookies from table'
    option_list = BaseCommand.option_list + (
        make_option('--offset',
            action='store',
            dest='offset',
            help='Select the amount of days to go back',
            default=180,
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
        total_cookies = Cookie.objects.filter(created__lt=purge_date).count()
        input_verified = options.get("input")

        if not total_cookies > 0:
            print "No cookies to purge!"
            return

        if not input_verified:
            prompt = "Will remove all cookies +{} : {} units. Are you sure? [Y/n]".format(purge_date, total_cookies)
            input_verified = bool(raw_input(prompt) == "Y")

        if input_verified:
            Cookie.objects.filter(created__lt=purge_date).delete()
        else:
            print "Canceling cookie purge"
