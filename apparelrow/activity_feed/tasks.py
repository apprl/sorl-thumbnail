import logging
import datetime
import redis
import json
import time

from django.utils import timezone
from django.db.models.loading import get_model

from celery.task import task

logger = logging.getLogger('activity_feed.tasks')


HARD_MAX = 100


def get_feed_key(profile, gender, private=False):
    if profile is None:
        return 'feed:%s:public' % (gender,)

    if private:
        return 'feed:%s:private:%s' % (gender, profile.pk)

    return 'feed:%s:%s' % (gender, profile.pk)


def get_score(activity):
    return time.mktime(activity.modified.timetuple())


def trim_feed(feed_key):
    keys = []
    r = redis.StrictRedis(host='localhost', port=6380, db=0)
    try:
        r.watch(feed_key)
        keys = r.zrevrange(feed_key, HARD_MAX, -1)
        pipe = r.pipeline()
        for key in keys:
            pipe.zrem(feed_key, key)
        pipe.execute()
    except redis.exceptions.WatchError:
        pass
    finally:
        r.unwatch()

    return keys

def remove_aggregate(user, gender, activity):
    r = redis.StrictRedis(host='localhost', port=6380, db=0)

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
                r.zrem(get_feed_key(user, gender), item_json)
                continue


def aggregate(user, gender, activity):
    """
    Aggregate activity for user.

    a stands for activities
    u stands for users
    ct stands for content type
    v stands for verb
    """
    r = redis.StrictRedis(host='localhost', port=6380, db=0)
    six_hours = time.mktime((activity.modified - datetime.timedelta(hours=6)).timetuple())

    # Special rule 1: if user is equal to activity.user this means that this is
    # a private feed and should be displayed on the users update page and we
    # want follow activity there.
    if activity.verb == 'follow' and user != activity.user:
        return

    # Special rule 2: if public feed and activity gender does not match gender do not add
    if user is None and activity.gender is not None and gender != activity.gender:
        return

    # Special rule 3: if user feed and activity is add product and activity
    # gender does not match gender do not add to feed
    if user is not None and activity.verb == 'add_product' and activity.gender is not None and gender != activity.gender:
        return

    # If user is same as activity.user we should store it using the private key
    feed_key = get_feed_key(user, gender)
    if activity.user == user:
        feed_key = get_feed_key(user, gender, private=True)

    count = r.zcount(feed_key, six_hours, '+inf')
    if count == 0:
        activity_json = json.dumps({'u': [activity.user.pk],
                                    'v': activity.verb,
                                    'ct': activity.content_type.pk,
                                    'a': [activity.pk]})
        r.zadd(feed_key, get_score(activity), activity_json)
    else:
        already_aggregated = False
        for item_json in r.zrevrangebyscore(feed_key, '+inf', six_hours):
            item = json.loads(item_json)
            if item['v'] == activity.verb and \
               item['ct'] == activity.content_type.pk:

                # Same user, only one user and activity object not already present
                if len(item['u']) == 1 and \
                   activity.user.pk in item['u'] and \
                   activity.pk not in item['a']:

                    # Special rule 4: do not aggregate objects for like_look and create
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
    trim_feed(feed_key)


@task(name='activity_feed.tasks.push_activity_feed', max_retries=5, ignore_result=True)
def push_activity_feed(activity):
    for followers in get_model('profile', 'follow').objects.followers(activity.user):
        aggregate(followers, 'M', activity)
        aggregate(followers, 'W', activity)

    aggregate(None, 'M', activity)
    aggregate(None, 'W', activity)

    aggregate(activity.user, 'M', activity)
    aggregate(activity.user, 'W', activity)


@task(name='activity_feed.tasks.pull_activity_feed', max_retries=5, ignore_result=True)
def pull_activity_feed(activity):
    for followers in get_model('profile', 'follow').objects.followers(activity.user):
        remove_aggregate(followers, 'M', activity)
        remove_aggregate(followers, 'W', activity)

    remove_aggregate(None, 'M', activity)
    remove_aggregate(None, 'W', activity)

    remove_aggregate(activity.user, 'M', activity)
    remove_aggregate(activity.user, 'W', activity)


@task(name='activity_feed.tasks.update_activity_feed', max_retries=5, ignore_result=True)
def update_activity_feed(profile, followee, add=True):
    Activity = get_model('activity_feed', 'activity')
    if add:
        since = datetime.datetime.now() - datetime.timedelta(days=30)
        for activity in Activity.objects.filter(user=followee,
                                                modified__gte=since,
                                                active=True):
            aggregate(profile, 'M', activity)
            aggregate(profile, 'W', activity)
    else:
        for activity in Activity.objects.filter(user=followee,
                                                active=True):
            remove_aggregate(profile, 'M', activity)
            remove_aggregate(profile, 'W', activity)
