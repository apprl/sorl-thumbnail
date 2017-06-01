import logging

from collections import defaultdict
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import mail_managers
from django.core.urlresolvers import reverse
from django.db import transaction

from apparelrow.dashboard.models import Payment, Sale, UserEarning, create_payment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    args = ''
    help = 'Process pending payments'

    @transaction.atomic
    def handle(self, *args, **options):
        earnings_per_user = defaultdict(list)

        # Get all publisher earnings that are confirmed and paid pending and group them by user
        for earning in UserEarning.objects.filter(status__gte=Sale.CONFIRMED, paid=Sale.PAID_PENDING, user_id__gt=0):
            earnings_per_user[earning.user].append(earning)

        for user, earnings in earnings_per_user.items():
            # Cancel any previous payments that haven't been paid out yet to this user and add them
            # to list of earnings that will be added to new payment
            for old_non_paid_payment in Payment.objects.filter(user=user, paid=False):
            for old_non_paid_payment in Payment.objects.filter(user=user, paid=False, cancelled=False):
                previous_earnings = old_non_paid_payment.cancel()
                earnings.extend(previous_earnings)

            # Only create new payment if user has reached minimum payout
            if sum(e.amount for e in earnings) >= settings.APPAREL_DASHBOARD_MINIMUM_PAYOUT:
                payment = create_payment(user, earnings)
                self.email_admins_about_new_payment(payment)

    def email_admins_about_new_payment(self, payment):
        subject = 'New dashboard payment'
        url = reverse("admin:dashboard_payment_change", args=[payment.pk])
        body = 'New dashboard payment available at %s for user %s.' % (url, payment.user)
        mail_managers(subject, body)
