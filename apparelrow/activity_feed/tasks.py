import logging
import datetime

from django.db.models.loading import get_model
from celery.task import task

logger = logging.getLogger('activity_feed.tasks')

@task(name='activity_feed.tasks.push_activity_feed', max_retries=5, ignore_result=True)
def push_activity_feed(profile, verb, content_type, object_id, data=None):
    Follow = get_model('profile', 'follow')
    ActivityFeed = get_model('activity_feed', 'activityfeed')

    defaults = {}
    if data is not None:
        defaults['data'] = data

    ActivityFeed.objects.get_or_create(owner=profile, user=profile, verb=verb, content_type=content_type, object_id=object_id, defaults=defaults)
    for followers in Follow.objects.followers(profile):
        ActivityFeed.objects.get_or_create(owner=followers, user=profile, verb=verb, content_type=content_type, object_id=object_id, defaults=defaults)


@task(name='activity_feed.tasks.pull_activity_feed', max_retries=5, ignore_result=True)
def pull_activity_feed(profile, verb, content_type, object_id):
    ActivityFeed = get_model('activity_feed', 'activityfeed')
    ActivityFeed.objects.filter(user=profile, verb=verb, content_type=content_type, object_id=object_id).delete()


@task(name='activity_feed.tasks.update_activity_feed', max_retries=5, ignore_result=True)
def update_activity_feed(profile, followee, add=True):
    Activity = get_model('activity_feed', 'activity')
    ActivityFeed = get_model('activity_feed', 'activityfeed')

    if add:
        last_month = datetime.datetime.now() - datetime.timedelta(days=30)
        for activity in Activity.objects.filter(user=followee,
                                                modified__gte=last_month,
                                                active=True):
            ActivityFeed.objects.get_or_create(owner=profile,
                                               user=followee,
                                               verb=activity.verb,
                                               content_type=activity.content_type,
                                               object_id=activity.object_id,
                                               defaults={'created': activity.created, 'data': activity.data})
    else:
        ActivityFeed.objects.filter(owner=profile, user=followee).delete()
