import datetime

from django.db.models.loading import get_model
from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType

from apparel.models import Brand, Product

class Command(BaseCommand):
    args = ''
    help = 'Check for brand updates'

    def handle(self, *args, **options):
        """
        Check for brand updates.

        Every time it is called it will iterate through all brands and check if
        any new products are added. If there are new products the task will
        create a new actstream action.
        """
        for brand in Brand.objects.iterator():
            first_product = None
            count_product = 0
            last_update = brand.last_update
            if last_update is None:
                last_update = datetime.datetime.now() - datetime.timedelta(days=365)
            for product in Product.valid_objects.filter(date_added__gt=last_update, manufacturer=brand).iterator():
                if first_product is None:
                    first_product = product
                count_product += 1

            if first_product is not None:
                action_object = get_model('actstream', 'Action') \
                                    .objects.get_or_create(actor_content_type=ContentType.objects.get_for_model(brand.profile.user),
                                                           actor_object_id=brand.profile.user.pk,
                                                           verb='added_products',
                                                           description=count_product,
                                                           action_object_content_type=ContentType.objects.get_for_model(first_product),
                                                           action_object_object_id=first_product.pk)
            brand.last_update = datetime.datetime.now()
            brand.save()
