import datetime
import decimal

from django.core.management.base import BaseCommand

from apparelrow.apparel.models import Look, LookLike
from apparelrow.apparel.utils import get_popularity

class Command(BaseCommand):
    args = ''
    help = 'Updates popularity for all looks (takes awhile)'

    def handle(self, *args, **options):
        oldest_look_timestamp = 1134028003

        for look in Look.objects.iterator():
            popularity = decimal.Decimal(str(LookLike.objects.filter(look=look, active=True).count() / 100000000.0))
            two_weeks_behind = datetime.datetime.now() - datetime.timedelta(weeks=2)
            like_count = LookLike.objects.filter(look=look, active=True, created__gte=two_weeks_behind).count()
            timedelta = datetime.datetime.now() - look.created
            item_half_hour_age =  (timedelta.days * 86400 + timedelta.seconds) / 7200
            if item_half_hour_age > 0:
                popularity += decimal.Decimal(str(like_count / pow(item_half_hour_age, 1.53)))

            popularity2 = get_popularity(like_count, look.created, oldest_look_timestamp)

            Look.objects.filter(pk=look.pk).update(popularity=popularity, popularity2=popularity2)
