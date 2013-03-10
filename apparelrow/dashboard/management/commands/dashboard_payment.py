import logging
import datetime

from django.conf import settings
from django.db.models.loading import get_model
from django.core.management.base import BaseCommand, CommandError

from apparelrow.dashboard.models import Payment, Sale


logger = logging.getLogger('dashboard.payment')


class Command(BaseCommand):
    args = ''
    help = 'Process pending payments'

    def handle(self, *args, **options):
        today = datetime.date.today()

        sales_per_user = {}
        sales_per_user_ids = {}
        for sale in Sale.objects.filter(status__gte=Sale.CONFIRMED, paid__lte=Sale.PAID_READY, user_id__gt=0):
            if sale.user_id not in sales_per_user:
                sales_per_user[sale.user_id] = 0
                sales_per_user_ids[sale.user_id] = []

            sales_per_user[sale.user_id] += sale.commission
            sales_per_user_ids[sale.user_id].append(sale.pk)

        for key, value in sales_per_user.items():
            if value > settings.APPAREL_DASHBOARD_MINIMUM_PAYOUT:
                try:
                    details = get_model('profile', 'PaymentDetail').objects.get(user=key)
                except get_model('profile', 'PaymentDetail').DoesNotExist:
                    logger.error('No payment details exist for user with id: %s' % (key,))
                    continue

                if details.company:
                    if not details.name or not details.orgnr:
                        logger.error('Payment details is for a company but is missing name or orgnr')
                        continue
                else:
                    if not details.name or not details.orgnr or not details.clearingnr or not details.banknr:
                        logger.error('Payment details is for a person but is missing name, orgnr or banknr')
                        continue

                # Update sale transactions to ready for payment
                Sale.objects.filter(pk__in=sales_per_user_ids[key]).update(paid=Sale.PAID_READY)

                # Cancel previous payments
                Payment.objects.filter(user_id=key).update(cancelled=True)

                # Create payment and make sure it is not cancelled
                payment, created = Payment.objects.get_or_create(user_id=key, details=details, amount=value)
                if not created:
                    payment.cancelled = False
                    payment.save()
