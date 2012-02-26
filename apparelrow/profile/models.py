import uuid
import os.path
import datetime

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.utils.translation import get_language, ugettext_lazy as _
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from actstream.models import Follow, Action
from sorl.thumbnail import get_thumbnail

from apparel.models import Look, LookLike, ProductLike
from apparel.utils import get_friend_updates

EVENT_CHOICES = (
    ('A', _('All')),
    ('F', _('Those I follow')),
    ('N', _('No one')),
)

def profile_image_path(instance, filename):
    return os.path.join(settings.APPAREL_PROFILE_IMAGE_ROOT, uuid.uuid4().hex)

GENDERS = ( ('M', 'Men'),
            ('W', 'Women'))

class ApparelProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    
    name                = models.CharField(max_length=50, unique=True, blank=True, null=True)
    image               = models.ImageField(upload_to=profile_image_path, help_text=_('User profile image'), blank=True, null=True) 
    about               = models.TextField(_('About'), null=True, blank=True)
    language            = models.CharField(_('Language'), max_length=10, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    gender              = models.CharField(_('Gender'), max_length=1, choices=GENDERS, null=True, blank=True, default=None)
    updates_last_visit  = models.DateTimeField(_('Last visit home'), default=datetime.datetime.now)

    num_updates_last_visit = None

    # notification settings
    comment_product_wardrobe = models.CharField(max_length=1, choices=EVENT_CHOICES, default='A',
            help_text=_('When someone commented on a product that I have in my wardrobe'))
    comment_product_comment = models.CharField(max_length=1, choices=EVENT_CHOICES, default='A',
            help_text=_('When someone commented on a product that I have commented on'))
    comment_look_created = models.CharField(max_length=1, choices=EVENT_CHOICES, default='A',
            help_text=_('When someone commented on a look that I have created'))
    comment_look_comment = models.CharField(max_length=1, choices=EVENT_CHOICES, default='A',
            help_text=_('When someone commented on a look that I have commented on'))
    like_look_created = models.CharField(max_length=1, choices=EVENT_CHOICES, default='A',
            help_text=_('When someone likes a look that I have created'))
    follow_user = models.CharField(max_length=1, choices=EVENT_CHOICES, default='A',
            help_text=_('When someone starts to follow me'))

    first_visit = models.BooleanField(default=True, blank=False, null=False,
            help_text=_('Is this the first visit?'))

    followers_count = models.IntegerField(default=0, blank=False, null=False)

    @models.permalink
    def get_looks_url(self):
        return ('looks_by_user', [str(self.user.username)])

    @property
    def looks(self):
        # Number of looks
        return Look.objects.filter(user=self.user).count()
    
    @property
    def likes(self):
        # Number of likes on products and looks combined
        return LookLike.objects.filter(user=self.user).count() + ProductLike.objects.filter(user=self.user).count()

    @property
    def display_name(self):
        if self.name is not None:
            return self.name
        
        if self.user.first_name:
            return u'%s %s' % (self.user.first_name, self.user.last_name)
         
        return u'%s' % self.user

    @property
    def avatar(self):
        if self.image:
            return get_thumbnail(self.image, '50x50', crop='center').url

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?type=square' % self.facebook_uid

        return settings.APPAREL_DEFAULT_AVATAR

    @property
    def avatar_medium(self):
        if self.image:
            return get_thumbnail(self.image, '125').url

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?type=normal' % self.facebook_uid

        return settings.APPAREL_DEFAULT_AVATAR

    @property
    def avatar_large(self):
        if self.image:
            return get_thumbnail(self.image, '200').url

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?type=large' % self.facebook_uid

        return settings.APPAREL_DEFAULT_AVATAR_LARGE

    @property
    def facebook_uid(self):
        """
        Try to convert username to int, if possible it is safe to assume that
        the user is a facebook-user and not an admin created user.
        """
        try:
            return int(self.user.username)
        except ValueError:
            pass

        return None

    @property
    def get_updates_last_visit(self):
        if self.num_updates_last_visit == None:
            self.num_updates_last_visit = get_friend_updates(self.user).filter(timestamp__gt=self.updates_last_visit).count()
        return self.num_updates_last_visit

    @models.permalink
    def get_absolute_url(self):
        return ('profile.views.profile', [str(self.user.username)])
    
    def __unicode__(self):
        return self.display_name

class EmailChange(models.Model):
    user = models.ForeignKey(User)
    token = models.CharField(max_length=42)
    email = models.CharField(max_length=256)

    def __unicode__(self):
        return '%s - %s' % (self.user, self.email)

#
# Create profile when a new user is created
#

def create_profile(signal, instance, **kwargs):
    if kwargs['created']:
        p, created = ApparelProfile.objects.get_or_create(user=instance)

post_save.connect(create_profile, sender=User)

#
# Delete follows and actions when a user is deleted.
#

def delete_user_followings(signal, instance, **kwargs):
    """
    This signal attempts to delete any followings which is related to Follow
    through a generic relation.
    """
    Follow.objects.filter(
        object_id=instance.pk,
        content_type=ContentType.objects.get_for_model(instance)
        ).delete()
    Follow.objects.filter(user=instance).delete()

# XXX: If actions get missing, look here...
def delete_object_activities(sender, instance, **kwargs):
    """
    This signal attempts to delete any activity which is related to Action
    through a generic relation. This should keep the Action table sane.
    """
    Action.objects.filter(
        action_object_object_id=instance.pk,
        action_object_content_type=ContentType.objects.get_for_model(instance)
        ).delete()
    Action.objects.filter(
        actor_object_id=instance.pk,
        actor_content_type=ContentType.objects.get_for_model(instance)
        ).delete()
    Action.objects.filter(
        target_object_id=instance.pk,
        target_content_type=ContentType.objects.get_for_model(instance)
        ).delete()


# FIXME: Move these to actstream?
post_delete.connect(delete_user_followings, sender=User)
post_delete.connect(delete_object_activities, sender=User)

#def delete_user_comments(signal, instance, **kwargs):
    #"""
    #This signal attemps to delete any comments which is written by the user.
    #"""
    #Comment.objects.filter(user=instance).delete()
#post_delete.connect(delete_user_comments, sender=User)

#
# NOTIFICATION CACHE
#

class NotificationCache(models.Model):
    key = models.CharField(max_length=255, unique=True, blank=False, null=False)

    def __unicode__(self):
        return '%s' % (self.key,)

import profile.activity
