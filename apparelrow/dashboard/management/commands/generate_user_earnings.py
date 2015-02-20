import logging
from django.core.management.base import BaseCommand
from django.db.models.loading import get_model
from apparelrow.dashboard.models import create_earnings


logger = logging.getLogger('dashboard.userearning')


class Command(BaseCommand):
    args = ''
    help = 'Generate User Earnings from existing sales'

    def handle(self, *args, **options):
        sales = get_model('dashboard', 'Sale').objects.all()
        for sale in sales:
            earnings_per_sale = get_model('dashboard', 'UserEarning').objects.filter(sale=sale)
            if len(earnings_per_sale) == 0:
                create_earnings(sale)
                for earning in get_model('dashboard', 'UserEarning').objects.filter(sale=sale):
                    earning.paid = get_model('dashboard', 'Sale').PAID_COMPLETE
                    earning.save()