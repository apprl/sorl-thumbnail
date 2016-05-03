from __future__ import print_function

import optparse
import logging
from datetime import date, timedelta
from calendar import monthrange

from django.core.management import call_command
from django.core.management.base import BaseCommand
from progressbar import ProgressBar, Percentage, Bar

logger = logging.getLogger('dashboard')

class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'
    option_list = BaseCommand.option_list + (
        optparse.make_option('--date',
            action='store',
            dest='date',
            help='Select date period YYYY-MM to run collect_aggregated_data command',
            default= None,
        ),
    )

    def handle(self, *args, **options):
        """
        Handler for job that aggregates data in general, for publishers and for products.
        Attention: This job does not handle correctly when a vendor has is_cpc=True and is_cpo=True, because
        they are exclusive among each other until the current time.
        """
        # Initialize date period
        date_array = options.get('date').split("-")
        year = int(date_array[0])
        month = int(date_array[1])

        start_date = date(year, month, 1)
        logger.debug("Starting aggregation of data for month period %s-%s" % (year, month))

        day_count = monthrange(year, month)[1]

        # Initialize progress bar
        pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=day_count).start()

        for single_date in (start_date + timedelta(n) for n in range(day_count)):
            pbar.update(single_date.day)
            call_command('collect_aggregated_data', date=single_date.strftime('%Y-%m-%d'), verbosity=0,
                         interactive=False)
        pbar.finish()
        logger.debug("Finishing aggregation of data for month period %s-%s" % (year, month))