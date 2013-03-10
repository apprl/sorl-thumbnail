import datetime
import decimal

from django.core.management.base import BaseCommand, CommandError

from apparelrow.apparel.models import Look, LookLike

class Command(BaseCommand):
    args = ''
    help = 'Updates popularity for all looks (takes awhile)'

    def handle(self, *args, **options):
        for look in Look.objects.iterator():
            popularity = decimal.Decimal(str(LookLike.objects.filter(look=look, active=True).count() / 100000000.0))
            two_weeks_behind = datetime.datetime.now() - datetime.timedelta(weeks=2)
            like_count = LookLike.objects.filter(look=look, active=True, created__gte=two_weeks_behind).count()
            timedelta = datetime.datetime.now() - look.created
            item_half_hour_age =  (timedelta.days * 86400 + timedelta.seconds) / 7200
            if item_half_hour_age > 0:
                popularity += decimal.Decimal(str(like_count / pow(item_half_hour_age, 1.53)))

            Look.objects.filter(pk=look.pk).update(popularity=popularity)
