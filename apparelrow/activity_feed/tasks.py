import logging
import datetime
import redis
import json
import time
import random

from django.conf import settings
from django.utils import timezone
from django.db.models.loading import get_model

from celery.task import task, periodic_task
from celery.schedules import crontab

logger = logging.getLogger('activity_feed.tasks')


HARD_MAX = 100

# XXX: private feed is not used anymore, should remove it from here and then remove this comment


def get_feed_key(profile, gender, private=False):
    if profile is None:
        return 'feed:%s:public' % (gender,)

    if private:
        return 'feed:%s:private:%s' % (gender, profile.pk)

    return 'feed:%s:%s' % (gender, profile.pk)


def get_score(activity):
    return time.mktime(activity.created.timetuple())


def trim_feed(r, feed_key):
    keys = []
    with r.pipeline() as pipe:
        try:
            pipe.watch(feed_key)
            keys = pipe.zrevrange(feed_key, HARD_MAX, -1)
            pipe.multi()
            for key in keys:
                pipe.zrem(feed_key, key)
            pipe.execute()
        except redis.exceptions.WatchError:
            pass

    return keys

def remove_aggregate(r, user, gender, activity):
    for item_json in r.zrevrangebyscore(get_feed_key(user, gender), '+inf', '-inf'):
        item = json.loads(item_json)

        # TODO: update new get_score correctly, should use another activities
        # score instead of the activity being removed
        if item['v'] == activity.verb and item['ct'] == activity.content_type.pk:
            if len(item['u']) > 1 and len(item['a']) > 1:
                removed = False
                if activity.user.pk in item['u']:
                    item['u'].remove(activity.user.pk)
                    removed = True
                if activity.pk in item['a']:
                    item['a'].remove(activity.pk)
                    removed = True

                if removed == True:
                    pipe = r.pipeline(transaction=True)
                    pipe.zrem(get_feed_key(user, gender), item_json)
                    pipe.zadd(get_feed_key(user, gender), get_score(activity), json.dumps(item))
                    pipe.execute()

            elif len(item['u']) == 1 and len(item['a']) > 1:
                if activity.pk in item['a']:
                    item['a'].remove(activity.pk)
                    pipe = r.pipeline(transaction=True)
                    pipe.zrem(get_feed_key(user, gender), item_json)
                    pipe.zadd(get_feed_key(user, gender), get_score(activity), json.dumps(item))
                    pipe.execute()

            elif len(item['u']) > 1 and len(item['a']) == 1:
                if activity.user.pk in item['u']:
                    item['u'].remove(activity.user.pk)
                    pipe = r.pipeline(transaction=True)
                    pipe.zrem(get_feed_key(user, gender), item_json)
                    pipe.zadd(get_feed_key(user, gender), get_score(activity), json.dumps(item))
                    pipe.execute()

            elif len(item['u']) == 1 and len(item['a']) == 1:
                if item['u'][0] == activity.user.pk and item['a'][0] == activity.pk:
                    r.zrem(get_feed_key(user, gender), item_json)


def aggregate(r, user, gender, activity):
    """
    Aggregate activity for user.

    a stands for activities
    u stands for users
    ct stands for content type
    v stands for verb
    """
    twelve_hours = time.mktime((timezone.now() - datetime.timedelta(hours=12)).timetuple())

    # Special rule 1: if user is equal to activity.user this means that this is
    # a private feed and should be displayed on the users update page and we
    # want follow activity there.
    if activity.verb == 'follow' and user != activity.user:
        return

    # Special rule 2: if public feed and activity gender does not match gender do not add
    if user is None and activity.gender is not None and gender != activity.gender:
        return

    # Special rule 3: if public feed and verb is add_product, do not add to public feed
    if user is None and activity.verb == 'add_product':
        return

    # Special rule 4: if user feed and activity is add product and activity
    # gender does not match gender do not add to feed
    if user is not None and activity.verb == 'add_product' and activity.gender is not None and gender != activity.gender:
        return

    # If user is same as activity.user we should store it using the private key
    feed_key = get_feed_key(user, gender)
    if activity.user == user:
        feed_key = get_feed_key(user, gender, private=True)

    count = r.zcount(feed_key, twelve_hours, '+inf')
    if count == 0:
        activity_json = json.dumps({'u': [activity.user.pk],
                                    'v': activity.verb,
                                    'ct': activity.content_type.pk,
                                    'a': [activity.pk]})
        r.zadd(feed_key, get_score(activity), activity_json)
    else:
        already_aggregated = False
        for item_json in r.zrevrangebyscore(feed_key, '+inf', twelve_hours):
            item = json.loads(item_json)
            if item['v'] == activity.verb and \
               item['ct'] == activity.content_type.pk:

                # Same user, only one user and activity object not already present
                if len(item['u']) == 1 and \
                   activity.user.pk in item['u'] and \
                   activity.pk not in item['a']:

                    # Special rule 5: do not aggregate objects for like_look and create
                    if activity.verb == 'like_look' or activity.verb == 'create':
                        continue

                    item['a'].append(activity.pk)

                    pipe = r.pipeline(transaction=True)
                    pipe.zrem(feed_key, item_json)
                    pipe.zadd(feed_key, get_score(activity), json.dumps(item))
                    pipe.execute()

                    already_aggregated = True
                    break

                # Same activity object, only one activity object and user not already present
                elif len(item['a']) == 1 and \
                     activity.pk in item['a'] and \
                     activity.user.pk not in item['u']:

                    item['u'].append(activity.user.pk)

                    pipe = r.pipeline(transaction=True)
                    pipe.zrem(feed_key, item_json)
                    pipe.zadd(feed_key, get_score(activity), json.dumps(item))
                    pipe.execute()

                    already_aggregated = True
                    break

                # Ignore duplicates
                elif activity.pk in item['a'] and activity.user.pk in item['u']:
                    already_aggregated = True
                    break

        # If we did not found an activity to aggregate with, just add it
        if already_aggregated == False:
            activity_json = json.dumps({'u': [activity.user.pk],
                                        'v': activity.verb,
                                        'ct': activity.content_type.pk,
                                        'a': [activity.pk]})
            r.zadd(feed_key, get_score(activity), activity_json)

    # Trim feed to 100 activity posts
    trim_feed(r, feed_key)


@task(name='activity_feed.tasks.push_activity_feed', max_retries=5, ignore_result=True)
def push_activity_feed(activity, pull_first=False):
    r = redis.StrictRedis(host=settings.CELERY_REDIS_HOST,
                          port=settings.CELERY_REDIS_PORT,
                          db=settings.FEED_REDIS_DB)
    for followers in get_model('profile', 'follow').objects.followers(activity.user):
        if pull_first:
            remove_aggregate(r, followers, 'M', activity)
            remove_aggregate(r, followers, 'W', activity)
        aggregate(r, followers, 'M', activity)
        aggregate(r, followers, 'W', activity)

    if pull_first:
        remove_aggregate(r, None, 'M', activity)
        remove_aggregate(r, None, 'W', activity)
    aggregate(r, None, 'M', activity)
    aggregate(r, None, 'W', activity)

    if pull_first:
        remove_aggregate(r, activity.user, 'M', activity)
        remove_aggregate(r, activity.user, 'W', activity)
    aggregate(r, activity.user, 'M', activity)
    aggregate(r, activity.user, 'W', activity)


@task(name='activity_feed.tasks.pull_activity_feed', max_retries=5, ignore_result=True)
def pull_activity_feed(activity):
    r = redis.StrictRedis(host=settings.CELERY_REDIS_HOST,
                          port=settings.CELERY_REDIS_PORT,
                          db=settings.FEED_REDIS_DB)
    for followers in get_model('profile', 'follow').objects.followers(activity.user):
        remove_aggregate(r, followers, 'M', activity)
        remove_aggregate(r, followers, 'W', activity)

    remove_aggregate(r, None, 'M', activity)
    remove_aggregate(r, None, 'W', activity)

    remove_aggregate(r, activity.user, 'M', activity)
    remove_aggregate(r, activity.user, 'W', activity)


@task(name='activity_feed.tasks.update_activity_feed', max_retries=5, ignore_result=True)
def update_activity_feed(profile, followee, add=True):
    r = redis.StrictRedis(host=settings.CELERY_REDIS_HOST,
                          port=settings.CELERY_REDIS_PORT,
                          db=settings.FEED_REDIS_DB)
    Activity = get_model('activity_feed', 'activity')
    if add:
        since = datetime.datetime.now() - datetime.timedelta(days=30)
        for activity in Activity.objects.filter(user=followee,
                                                created__gte=since,
                                                active=True):
            aggregate(r, profile, 'M', activity)
            aggregate(r, profile, 'W', activity)
    else:
        for activity in Activity.objects.filter(user=followee,
                                                active=True):
            remove_aggregate(r, profile, 'M', activity)
            remove_aggregate(r, profile, 'W', activity)


@periodic_task(name='activity_feed.tasks.featured_activity', run_every=crontab(hour='23'), max_retries=1, ignore_result=True)
def featured_activity(next_day=True):
    Activity = get_model('activity_feed', 'activity')
    since = datetime.datetime.now() - datetime.timedelta(days=90)

    switch_activity_verb = {'like_product': 'create', 'create': 'like_product'}

    break_inf_loop = 0
    exclude_uids = []
    activity_list = []
    activity_verb = random.choice(switch_activity_verb.keys())
    while len(activity_list) < 3:
        activity = Activity.objects.filter(verb=activity_verb,
                                           created__gte=since,
                                           active=True,
                                           is_available=True
                                           featured_date__isnull=True) \
                                   .exclude(user_id__in=exclude_uids) \
                                   .order_by('-user__is_partner', '-user__popularity')[:1]
        if activity:
            activity = activity[0]
            exclude_uids.append(activity.user_id)
            activity_list.append(activity)
        else:
            activity = Activity.objects.filter(verb=activity_verb,
                                               active=True,
                                               is_available=True,
                                               featured_date__isnull=True) \
                                       .exclude(user_id__in=exclude_uids) \
                                       .order_by('-user__is_partner', '-user__popularity')[:1]
            if activity:
                activity = activity[0]
                exclude_uids.append(activity.user_id)
                activity_list.append(activity)

        activity_verb = switch_activity_verb.get(activity_verb)

        break_inf_loop = break_inf_loop + 1
        if break_inf_loop > 10:
            break

    if next_day:
        day = datetime.date.today() + datetime.timedelta(days=1)
    else:
        day = datetime.date.today()

    if not Activity.objects.filter(featured_date=day).exists():
        for activity in activity_list:
            activity.featured_date = day
            activity.save()
