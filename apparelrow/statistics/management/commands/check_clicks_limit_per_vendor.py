from django.db.models import get_model
from django.core.mail import mail_admins
from django.core.management.base import BaseCommand
from django.conf import settings
import datetime
import calendar
from apparelrow.statistics.utils import check_vendor_has_reached_limit

class Command(BaseCommand):
    args = ''
    help = 'Checks for every vendor if the limit of clicks have been reached on the current month and ' \
           'send a mail to admins'

    def handle(self, *args, **options):
        start_date = datetime.date.today().replace(day=1)
        end_date = start_date
        end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        vendor_list = get_model('apparel', 'Vendor').objects.filter(is_cpc=True)
        for vendor in vendor_list:
            if vendor.is_cpc:
                has_reached_limit = check_vendor_has_reached_limit(vendor, start_date, end_date)

                # Mail admins if limit has been reached
                if has_reached_limit:
                    mail_admins('Clicks limit reached', 'Limit for clicks for vendor %s has been reached' % vendor.name)