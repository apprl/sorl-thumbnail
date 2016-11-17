import logging
import datetime
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.core.management.base import BaseCommand
from django.core.mail import mail_managers
from django.core.urlresolvers import reverse
from django.db import transaction


from apparelrow.dashboard.models import Payment, Sale, UserEarning
from apparelrow.profile.models import User, PaymentDetail

MAX_LENGHT_EARNINGS_FIELD = 100
logger = logging.getLogger('dashboard')
#logger = logging.getLogger('dashboard.payment')


class Command(BaseCommand):
    args = ''
    help = 'Process pending payments'

    def handle(self, *args, **options):
        today = datetime.date.today()
        sales_per_user = {}
        sales_per_user_ids = {}

        with transaction.atomic():
            for earning in UserEarning.objects.filter(status__gte=Sale.CONFIRMED, paid__lte=Sale.PAID_READY, user_id__gt=0):
                if earning.user:
                    if earning.user.id not in sales_per_user:
                        sales_per_user[earning.user.id] = 0
                        sales_per_user_ids[earning.user.id] = []

                    sales_per_user[earning.user.id] += earning.amount
                    sales_per_user_ids[earning.user.id].append(earning.pk)

            for key, value in sales_per_user.items():
                if value > settings.APPAREL_DASHBOARD_MINIMUM_PAYOUT:
                    try:
                        user = User.objects.get(pk=key)
                        details, created = PaymentDetail.objects.get_or_create(user=user)

                        # Update sale transactions to ready for payment
                        UserEarning.objects.filter(pk__in=sales_per_user_ids[key]).update(paid=Sale.PAID_READY)

                        # Cancel previous payments that haven't been paid out yet
                        Payment.objects.filter(user_id=key, paid=False).update(cancelled=True)

                        # Not chopped string that include all the UserEarnings
                        json_earnings = json.dumps(sales_per_user_ids[key])

                        stored_earnings = json_earnings

                        if len(stored_earnings) > (MAX_LENGHT_EARNINGS_FIELD - 5):
                            stored_earnings = "%s%s" % (stored_earnings[:MAX_LENGHT_EARNINGS_FIELD - 5], "... }")

                        # Create payment and make sure it is not cancelled
                        payment, created = Payment.objects.get_or_create(user_id=key,
                                                                         details=details,
                                                                         amount=value,
                                                                         earnings=stored_earnings)
                        logger.info("Saved payment %s that includes the following UserEarnings %s" %(payment.id, json_earnings))
                        if not created:
                            payment.cancelled = False
                            payment.save()

                        url = reverse("admin:dashboard_payment_change", args=[payment.pk])
                        mail_managers('New dashboard payment', 'New dashboard payment available at %s for user id %s.' % (url, key))
                    except Exception as e:
                        logger.warning("Exception: %s (%s)") % (e.message, type(e))
