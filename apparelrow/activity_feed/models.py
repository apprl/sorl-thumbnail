import logging

from django.conf import settings
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone


from apparelrow.activity_feed.tasks import push_activity_feed
from apparelrow.activity_feed.tasks import pull_activity_feed

logger = logging.getLogger('activity_feed.models')


#
# ACTIVITY
#

class ActivityManager(models.Manager):
    """

    """
    def push_activity(self, profile, verb, activity_object, gender=None):
        if profile.is_hidden:
            logger.info("Don't push activity for hidden user: %s" % (profile.id,))
            return None

        if gender is not None and gender not in ['M', 'W']:
            gender = None
        content_type = ContentType.objects.get_for_model(activity_object)
        activity, created = self.get_or_create(user=profile,
                                               verb=verb,
                                               content_type=content_type,
                                               object_id=activity_object.pk,
                                               defaults={'active': True, 'gender': gender})
        if not created:
            activity.gender = gender
            activity.active = True
            activity.save()

        # Start task, add to all feeds
        push_activity_feed.delay(activity, pull_first=True)

    def pull_activity(self, profile, verb, activity_object):
        content_type = ContentType.objects.get_for_model(activity_object)
        try:
            activity = self.get(user=profile, verb=verb, content_type=content_type, object_id=activity_object.pk)
            activity.active = False
            activity.save()
            pull_activity_feed.delay(activity)
        except Activity.DoesNotExist:
            pass

    def update_activity(self, activity_object):
        content_type = ContentType.objects.get_for_model(activity_object)

        if content_type.app_label == 'apparel' and content_type.model == 'product':
            available = False
            if activity_object.availability and activity_object.default_vendor and activity_object.default_vendor.availability != 0:
                available = True

            self.filter(content_type=content_type, object_id=activity_object.pk).update(is_available=available)

        elif content_type.app_label == 'apparel' and content_type.model == 'look':
            available = False
            if activity_object.published:
                available = True

            self.filter(content_type=content_type, object_id=activity_object.pk).update(is_available=available)

    def get_for_user(self, user):
        return Activity.objects.filter(user=user, active=True) \
                               .select_related('user', 'owner') \
                               .prefetch_related('activity_object', 'content_type') \
                               .order_by('-created')


GENDERS = ( ('M', 'Men'),
            ('W', 'Women'))


class Activity(models.Model):
    """
    Original activity on format USER VERB OBJECT.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='activities', on_delete=models.CASCADE)
    verb = models.CharField(max_length=16)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    activity_object = generic.GenericForeignKey('content_type', 'object_id')
    gender = models.CharField(max_length=1, choices=GENDERS, null=True, blank=True, default=None)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(_('Time modified'), default=timezone.now, null=True, blank=True)
    active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    featured_date = models.DateField(null=True, blank=True, db_index=True)
    object_count = models.PositiveIntegerField(default=1)

    objects = ActivityManager()

    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        super(Activity, self).save(*args, **kwargs)

    def get_template(self):
        return 'activity_feed/verbs/%s.html' % (self.verb,)

    def __unicode__(self):
        return u'%s %s (%s %s)' % (self.user, self.verb, self.content_type, self.object_id)

    class Meta:
        unique_together = ('user', 'verb', 'content_type', 'object_id')
        index_together = [
            ['active', 'verb', 'is_available', 'user', 'gender'],
            ['active', 'featured_date'],
            ['content_type', 'object_id'],
        ]

@receiver(pre_delete, sender=Activity, dispatch_uid='activity_feed.models.delete_activity')
def delete_activity(sender, instance, **kwargs):
    """
    On delete activity remove all activity from feeds.
    """
    pull_activity_feed.delay(instance)

#
# ACTIVITY FEED
#

class ActivityFeedManager(models.Manager):
    """
    """
    def get_for_user(self, user):
        return ActivityFeed.objects.filter(owner=user, verb__in=['like_product', 'like_look', 'create', 'add_product']) \
                                   .exclude(user=user) \
                                   .select_related('user', 'owner') \
                                   .prefetch_related('activity_object', 'content_type') \
                                   .order_by('-created')

class ActivityFeed(models.Model):
    """
    An actitivty feed per user. Duplicates data from activity model for every
    connected user.
    """
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='activity_feeds', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.CASCADE)
    verb = models.CharField(max_length=16)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    activity_object = generic.GenericForeignKey('content_type', 'object_id')
    data = models.TextField(default='')
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)

    objects = ActivityFeedManager()

    def __unicode__(self):
        return u'%s <%s %s (%s %s)>' % (self.owner, self.user, self.verb, self.content_type, self.object_id)

    class Meta:
        unique_together = ('owner', 'user', 'verb', 'content_type', 'object_id')
