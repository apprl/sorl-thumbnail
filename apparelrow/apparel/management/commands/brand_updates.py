import datetime

from django.db.models.loading import get_model
from django.core.management.base import BaseCommand

from apparel.models import Brand, Product

class Command(BaseCommand):
    args = ''
    help = 'Check for brand updates'

    def handle(self, *args, **options):
        """
        Check for brand updates.

        Every time it is called it will iterate through all brands and check if
        any new products are added. If there are new products the task will
        create a new activity.
        """
        for brand in Brand.objects.iterator():
            last_update = brand.last_update
            if last_update is None:
                last_update = datetime.datetime.now() - datetime.timedelta(days=30)

            for product in Product.valid_objects.filter(date_added__gt=last_update, manufacturer=brand).order_by('-modified').iterator():
                get_model('activity_feed', 'activity').objects.push_activity(brand.profile, 'add_product', product, product.gender)

            brand.last_update = datetime.datetime.now()
            brand.save()
