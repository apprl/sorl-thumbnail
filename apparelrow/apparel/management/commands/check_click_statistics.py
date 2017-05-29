from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.signals import post_save
from django.core.mail import mail_admins
# from datetime import datetime, date, timedelta
import datetime

from apparelrow.profile.models import User
from apparelrow.statistics.models import ProductStat

class Command(BaseCommand):
    args = ''
    # cache_key = "vendor_product_history_{}"
    help = 'Checking the clicks for the last day'
    option_list = BaseCommand.option_list + (
        make_option('--email',
                    action='store_true',
                    dest='email',
                    default=False,
                    help='Send a report via email'),
        make_option('--date',
                    action='store',
                    dest='date',
                    help='Select a custom date in the format YYYY-MM-DD',
                    default=None,
                    )
    )

    def log(self, message):
        if self.email:
            self.log_buffer.append(message)
        else:
            print message

    def finish(self):
        if self.email:
            mail_admins('ApparelRow Clicks Due Diligence Report', '\n'.join(self.log_buffer))

    def handle(self, *args, **options):
        str_date = options.get("date", None)

        if str_date:
            start_date_query = datetime.datetime.strptime(str_date, '%Y-%m-%d')
            end_date_query = start_date_query
        else:
            start_date_query = datetime.date.today()
            end_date_query = start_date_query

        start_date = datetime.datetime.combine(start_date_query, datetime.time(0, 0, 0, 0))
        end_date = datetime.datetime.combine(end_date_query, datetime.time(23, 59, 59, 999999))

        results = ProductStat.objects.filter(created__range=(start_date, end_date)).values('user_id').annotate(
            clicks=Count('user_id')).order_by("-clicks")[:20]

        self.email = False
        if options.get('email'):
            self.email = True
            self.log_buffer = []

        self.log("\n\n################# {} - {} #################".format(start_date, end_date))
        for result in results:
            result.update({"name": " ".join(User.objects.filter(pk=result.get("user_id")).values_list("first_name", "last_name")[0])})
            self.log(u"{name} {user_id}: {clicks}".format(**result))

        self.finish()
