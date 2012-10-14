import logging

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from activity_feed.tasks import push_activity_feed
from activity_feed.tasks import pull_activity_feed
from activity_feed.tasks import update_activity_feed

logger = logging.getLogger('activity_feed.models')

#
# ACTIVITY
#

class ActivityManager(models.Manager):
    """

    """
    def push_activity(self, profile, verb, activity_object):
        content_type = ContentType.objects.get_for_model(activity_object)
        activity, created = self.get_or_create(user=profile,
                                               verb=verb,
                                               content_type=content_type,
                                               object_id=activity_object.pk)
        if not created and activity.active == False:
            activity.active = True
            activity.save()

        # Start task, add to all feeds
        push_activity_feed.delay(profile, verb, content_type, activity_object.pk)

    def pull_activity(self, profile, verb, activity_object):
        content_type = ContentType.objects.get_for_model(activity_object)
        self.filter(user=profile, verb=verb, content_type=content_type, object_id=activity_object.pk).update(active=False)

        # Start task, remove from all feeds
        pull_activity_feed.delay(profile, verb, content_type, activity_object.pk)

    def get_for_user(self, user):
        return Activity.objects.filter(user=user) \
                               .select_related('user', 'owner') \
                               .prefetch_related('activity_object', 'content_type') \
                               .order_by('-created')


class Activity(models.Model):
    """
    Original activity on format USER VERB OBJECT.
    """
    user = models.ForeignKey('profile.ApparelProfile', related_name='activities', on_delete=models.CASCADE)
    verb = models.CharField(max_length=16)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    activity_object = generic.GenericForeignKey('content_type', 'object_id')
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(_('Time modified'), default=timezone.now, null=True, blank=True)
    active = models.BooleanField(default=True, db_index=True)

    objects = ActivityManager()

    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        super(Activity, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'%s %s (%s %s)' % (self.user, self.verb, self.content_type, self.object_id)

    class Meta:
        unique_together = ('user', 'verb', 'content_type', 'object_id')


#
# ACTIVITY FEED
#

class ActivityFeedManager(models.Manager):
    """
    """
    def get_for_user(self, user):
        return ActivityFeed.objects.filter(owner=user) \
                                   .exclude(user=user) \
                                   .select_related('user', 'owner') \
                                   .prefetch_related('activity_object', 'content_type') \
                                   .order_by('-created')

class ActivityFeed(models.Model):
    """
    An actitivty feed per user. Duplicates data from activity model for every
    connected user.
    """
    owner = models.ForeignKey('profile.ApparelProfile', related_name='activity_feeds', on_delete=models.CASCADE)
    user = models.ForeignKey('profile.ApparelProfile', related_name='+', on_delete=models.CASCADE)
    verb = models.CharField(max_length=16)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    activity_object = generic.GenericForeignKey('content_type', 'object_id')
    data = models.TextField()
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)

    objects = ActivityFeedManager()

    def __unicode__(self):
        return u'%s <%s %s (%s %s)>' % (self.owner, self.user, self.verb, self.content_type, self.object_id)

    class Meta:
        unique_together = ('owner', 'user', 'verb', 'content_type', 'object_id')
