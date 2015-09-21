from django.db.models import get_model
from django.core.mail import mail_admins
from django.core.management.base import BaseCommand
from django.conf import settings
import datetime
import calendar

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
                clicks_limit = vendor.clicks_limit if vendor.clicks_limit else settings.APPAREL_DEFAULT_CLICKS_LIMIT
                clicks_amount = get_model('statistics', 'ProductStat').objects.\
                    filter(vendor=vendor.name, created__range=(start_date, end_date)).count()
                if clicks_amount >= clicks_limit:
                    if not vendor.is_limit_reached:
                        mail_admins('Clicks limit reached', 'Limit for clicks for vendor %s has been reached' % vendor.name)
                        vendor.is_limit_reached = True
                        vendor.save()
                elif vendor.is_limit_reached:
                    vendor.is_limit_reached = False
                    vendor.save()