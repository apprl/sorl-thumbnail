import datetime

import redis

from django.conf import settings
from django.db.models.loading import get_model
from django.core.management.base import BaseCommand

from activity_feed.tasks import aggregate

class Command(BaseCommand):
    args = ''
    help = 'Activity updates'

    def handle(self, *args, **options):
        """
        Update redis activities based on found in Activity model.
        """
        r = redis.StrictRedis(host=settings.CELERY_REDIS_HOST,
                              port=settings.CELERY_REDIS_PORT,
                              db=settings.FEED_REDIS_DB)
        since = datetime.datetime.now() - datetime.timedelta(days=90)
        for activity in get_model('activity_feed', 'activity').objects.filter(modified__gte=since, active=True).order_by('modified'):
            aggregate(r, None, 'M', activity)
            aggregate(r, None, 'W', activity)
            aggregate(r, activity.user, 'M', activity)
            aggregate(r, activity.user, 'W', activity)
            for followers in get_model('profile', 'follow').objects.filter(user_follow=activity.user, active=True).select_related('user'):
                aggregate(r, followers.user, 'M', activity)
                aggregate(r, followers.user, 'W', activity)
