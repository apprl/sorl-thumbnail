import datetime
import redis

from django.conf import settings
from django.db.models.loading import get_model
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

from apparel.models import Brand, Product
from activity_feed.tasks import aggregate

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
        r = redis.StrictRedis(host=settings.CELERY_REDIS_HOST,
                              port=settings.CELERY_REDIS_PORT,
                              db=settings.FEED_REDIS_DB)

        content_type = ContentType.objects.get_for_model(Product)
        for brand in Brand.objects.iterator():
            last_update = brand.last_update
            if last_update is None:
                last_update = datetime.datetime.now() - datetime.timedelta(days=30)

            for product in Product.valid_objects.filter(date_added__gt=last_update, manufacturer=brand).order_by('-modified').iterator():
                #get_model('activity_feed', 'activity').objects.push_activity(brand.user, 'add_product', product, product.gender)
                # Code below is taken from activity_feed.models and
                # activity_feed.task because we do not want to use a new redis
                # connection for every product
                activity, created = get_model('activity_feed', 'activity') \
                        .objects.get_or_create(user=brand.user,
                                               verb='add_product',
                                               content_type=content_type,
                                               object_id=product.pk,
                                               defaults={'active': True, 'gender': product.gender})
                if not created and activity.active == False:
                    activity.active = True
                    activity.save()

                for followers in get_model('profile', 'follow').objects.followers(activity.user):
                    aggregate(r, followers, 'M', activity)
                    aggregate(r, followers, 'W', activity)
                aggregate(r, None, 'M', activity)
                aggregate(r, None, 'W', activity)
                aggregate(r, brand.profile, 'M', activity)
                aggregate(r, brand.profile, 'W', activity)

            brand.last_update = datetime.datetime.now()
            brand.save()
