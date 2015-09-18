import logging
import datetime
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.core.management.base import BaseCommand
from django.core.mail import mail_managers
from django.core.urlresolvers import reverse

from apparelrow.dashboard.models import Payment, Sale, UserEarning


logger = logging.getLogger('dashboard.payment')


class Command(BaseCommand):
    args = ''
    help = 'Process pending payments'

    def handle(self, *args, **options):
        today = datetime.date.today()
        sales_per_user = {}
        sales_per_user_ids = {}

        for earning in UserEarning.objects.filter(status__gte=Sale.CONFIRMED, paid__lte=Sale.PAID_READY, user_id__gt=0):
            if earning.user:
                if earning.user.id not in sales_per_user:
                    sales_per_user[earning.user.id] = 0
                    sales_per_user_ids[earning.user.id] = []

                sales_per_user[earning.user.id] += earning.amount
                sales_per_user_ids[earning.user.id].append(earning.pk)

        for key, value in sales_per_user.items():
            if value > settings.APPAREL_DASHBOARD_MINIMUM_PAYOUT:
                user = get_user_model().objects.get(pk=key)
                details, created = get_model('profile', 'PaymentDetail').objects.get_or_create(user=user)

                # Update sale transactions to ready for payment
                UserEarning.objects.filter(pk__in=sales_per_user_ids[key]).update(paid=Sale.PAID_READY)

                # Cancel previous payments
                Payment.objects.filter(user_id=key).update(cancelled=True)

                # Create payment and make sure it is not cancelled
                payment, created = Payment.objects.get_or_create(user_id=key, details=details, amount=value,
                                                                 earnings=json.dumps(sales_per_user_ids[key]))
                if not created:
                    payment.cancelled = False
                    payment.save()

                url = reverse("admin:dashboard_payment_change", args=[payment.pk])
                mail_managers('New dashboard payment', 'New dashboard payment available at %s' % (url,))
