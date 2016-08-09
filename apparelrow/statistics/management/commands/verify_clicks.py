import optparse
from django.db.models import get_model
from django.core.management.base import BaseCommand
from django.conf import settings
from progressbar import ProgressBar, Percentage, Bar
from apparelrow.statistics.utils import get_country_by_ip_string


class Command(BaseCommand):
    args = ''
    help = 'Run verification on clicks'
    option_list = BaseCommand.option_list + (
        optparse.make_option('--date',
            action='store',
            dest='date',
            help='Select a custom date in the format YYYY-MM-DD',
            default= None,
        ),
        optparse.make_option('--all-clicks',
            action='store_true',
            dest='all_clicks',
            help='All clicks not just those non verified',
            default=False,
        ),
        optparse.make_option('--dry',
            action='store_true',
            dest='dry',
            default=False,
            help='Dry run, do not updated any clicks',
        ),
        optparse.make_option('--vendor',
            action='store',
            dest='vendor',
            help='Filter clicks on vendor name as it appears in the ProductStat table.',
            default= None,
        ),
    )
    def handle(self, *args, **options):
        """
        Tiny gotcha I found testing this. First I ran
        python manage.py verify_clicks --date=2016-06-23
        Found 341 clicks to check                                                                      |
        100%|##########################################################################################|
        47 product clicks has been updated.

        Then after that I ran the same day again which should give you zero updates, right? It may, but most likely you will get this
        python manage.py verify_clicks --date=2016-06-23
        Found 299 clicks to check                                                                      |
        100%|##########################################################################################|
        5 product clicks has been updated.

        Why would there still be clicks that could be corrected? Answer: The distinct part of the query excludes duplicate
        clicks the first round but includes them the second go around.
        :param args:
        :param options:
        :return:
        """

        from datetime import datetime, date, timedelta

        filters = {}
        distinct_fields = ['ip', 'page', 'product']
        dry_run = options.get("dry")

        if not options.get("date", None):
            date_created = date.today()
        else:
            date_created = datetime.strptime(options.get("date"), '%Y-%m-%d')
        filters.update({"created__range": [date_created, date_created + timedelta(days=1)], "product__isnull": False})

        if options.get("vendor", None):
            filters.update({"vendor": options.get("vendor")})
        else:
            distinct_fields.append('vendor')

        if not options.get("all_clicks", None):
            filters.update({"is_valid": False})
        print filters

        clicks = get_model('statistics', 'ProductStat').objects.filter(**filters).order_by(*distinct_fields).distinct(*distinct_fields)
        updated = 0
        if clicks.count() > 0:
            pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=clicks.count()).start()
            print "Found {} clicks to check".format(clicks.count())
            for index, click in enumerate(clicks.iterator()):
                pbar.update(index)
                country = get_country_by_ip_string(click.ip, timeout=10.0)

                # This violates the DRY principle as this code is already present in def product_buy_click in statistics/tasks.py
                # Todo: Refactor this

                vendor_markets = settings.VENDOR_LOCATION_MAPPING.get(click.vendor, [])
                if not vendor_markets or len(vendor_markets) == 0:
                    vendor_markets = settings.VENDOR_LOCATION_MAPPING.get("default")

                if country in vendor_markets:
                    if not dry_run:
                        click.is_valid=True
                        click.save()
                    updated += 1
                #print get_country_by_ip_string(click.ip)
            pbar.finish()
            print "{} product clicks has been updated.".format(updated)
        else:
            print "No clicks found for period {}".format(date_created)