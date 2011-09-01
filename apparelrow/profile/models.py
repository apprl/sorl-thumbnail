import uuid
import os.path

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.utils.translation import get_language, ugettext_lazy as _
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django_facebook.models import FacebookProfile
from actstream.models import Follow, Action

from apparel.models import Look, LookLike, ProductLike

EVENT_CHOICES = (
    ('A', _('All')),
    ('F', _('Those I follow')),
    ('N', _('No one')),
)

def profile_image_path(instance, filename):
    return os.path.join(settings.APPAREL_PROFILE_IMAGE_ROOT, uuid.uuid4().hex)

class ApparelProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    
    name = models.CharField(max_length=50, unique=True, blank=True, null=True)
    image = models.ImageField(upload_to=profile_image_path, help_text=_('User profile image'), blank=True, null=True) 
    about = models.TextField(_('About'), null=True, blank=True)
    language = models.CharField(_('Language'), max_length=10, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)

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

    # FIXME: Extract number of looks and and likes

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
            return '/scale/50x50%s?crop=true' % self.image

        if self.facebook_profile:
            return 'http://graph.facebook.com/%s/picture?type=square' % self.facebook_profile.uid

        return settings.APPAREL_DEFAULT_AVATAR

    @property
    def avatar_medium(self):
        if self.image:
            return '/scale/125%s' % self.image

        if self.facebook_profile:
            return 'http://graph.facebook.com/%s/picture?type=small' % self.facebook_profile.uid

        return settings.APPAREL_DEFAULT_AVATAR

    @property
    def avatar_large(self):
        if self.image:
            return '/scale/200%s' % self.image

        if self.facebook_profile:
            return 'http://graph.facebook.com/%s/picture?type=large' % self.facebook_profile.uid

        return settings.APPAREL_DEFAULT_AVATAR_LARGE

    @property
    def facebook_profile(self):
        try:
            return FacebookProfile.objects.get(user=self.user)
        except FacebookProfile.DoesNotExist:
            return None

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

def create_profile(signal, instance, **kwargs):
    if kwargs['created']:
        p, created = ApparelProfile.objects.get_or_create(user=instance)

def create_profile_from_facebook(signal, instance, **kwargs):
    if kwargs['created']:
        fb_properties = {
            'name': instance.name,
            'about': instance.bio,
        }
        p, created = ApparelProfile.objects.get_or_create(user=instance.user, defaults=fb_properties)

        if not created:
            p.name = instance.name
            p.about = instance.bio
            p.save()

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

post_save.connect(create_profile, sender=User)
post_save.connect(create_profile_from_facebook, sender=FacebookProfile)

# FIXME: Move these to actstream?
post_delete.connect(delete_user_followings, sender=User)
post_delete.connect(delete_object_activities, sender=User)

import profile.activity
