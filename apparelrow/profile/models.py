# coding=utf-8

import uuid
import os.path
import datetime

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.utils.translation import get_language, ugettext_lazy as _
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from django.template.defaultfilters import slugify

from actstream import models as actstream_models
from sorl.thumbnail import get_thumbnail
from django_extensions.db.fields import AutoSlugField

from profile.tasks import send_email_confirm_task
from profile.signals import user_created_with_email

EVENT_CHOICES = (
    ('A', _('All')),
    ('F', _('Those I follow')),
    ('N', _('No one')),
)

def profile_image_path(instance, filename):
    return os.path.join(settings.APPAREL_PROFILE_IMAGE_ROOT, uuid.uuid4().hex)

GENDERS = ( ('M', 'Men'),
            ('W', 'Women'))

LOGIN_FLOW = (
    ('initial', 'Initial'),
    ('members', 'Members'),
    ('brands', 'Brands'),
    ('complete', 'Complete'),
)

class ApparelProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    
    name                = models.CharField(max_length=100, unique=True, blank=True, null=True)
    slug                = models.CharField(max_length=100, unique=True, null=True)
    image               = models.ImageField(upload_to=profile_image_path, help_text=_('User profile image'), blank=True, null=True) 
    about               = models.TextField(_('About'), null=True, blank=True)
    language            = models.CharField(_('Language'), max_length=10, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    gender              = models.CharField(_('Gender'), max_length=1, choices=GENDERS, null=True, blank=True, default=None)
    updates_last_visit  = models.DateTimeField(_('Last visit home'), default=datetime.datetime.now)

    # brand profile
    is_brand = models.BooleanField(default=False)
    brand = models.OneToOneField('apparel.Brand', default=None, blank=True, null=True, on_delete=models.SET_NULL, related_name='profile')

    # profile login flow
    login_flow = models.CharField(_('Login flow'), max_length=20, choices=LOGIN_FLOW, null=False, blank=False, default='initial')

    # newsletter settings
    newsletter = models.BooleanField(default=True, blank=False, null=False, help_text=_('Participating in newsletter'))

    # share settings
    fb_share_like_product = models.BooleanField(default=False, blank=False, null=False)
    fb_share_like_look = models.BooleanField(default=False, blank=False, null=False)
    fb_share_follow_profile = models.BooleanField(default=False, blank=False, null=False)
    fb_share_create_look = models.BooleanField(default=False, blank=False, null=False)

    # facebook
    facebook_access_token = models.CharField(max_length=255, null=True, blank=True)
    facebook_access_token_expire = models.DateTimeField(null=True, blank=True)

    # notification settings
    comment_product_wardrobe = models.CharField(max_length=1, choices=EVENT_CHOICES, default='A',
            help_text=_('When someone commented on a product that I have liked'))
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

    # XXX: make this a real column on the model?
    @property
    def has_liked(self):
        """User has liked"""
        return self.user.product_likes.exists()

    @property
    def looks(self):
        """Number of looks"""
        return self.user.look.count()
    
    @property
    def likes(self):
        """Number of likes on products and looks combined"""
        return self.user.look_likes.filter(active=True).count() + self.user.product_likes.filter(active=True).count()

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

        if self.is_brand:
            return settings.APPAREL_DEFAULT_BRAND_AVATAR

        return settings.APPAREL_DEFAULT_AVATAR

    @property
    def avatar_medium(self):
        if self.image:
            return get_thumbnail(self.image, '125').url

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?type=normal' % self.facebook_uid

        if self.is_brand:
            return settings.APPAREL_DEFAULT_BRAND_AVATAR_MEDIUM

        return settings.APPAREL_DEFAULT_AVATAR

    @property
    def avatar_large(self):
        if self.image:
            return get_thumbnail(self.image, '200').url

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?type=large' % self.facebook_uid

        if self.is_brand:
            return settings.APPAREL_DEFAULT_BRAND_AVATAR_LARGE

        return settings.APPAREL_DEFAULT_AVATAR_LARGE

    def avatar_large_absolute_uri(self, request):
        if self.image:
            return request.build_absolute_uri(get_thumbnail(self.image, '200').url)

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?type=large' % self.facebook_uid

        if self.is_brand:
            return request.build_absolute_uri(settings.APPAREL_DEFAULT_AVATAR_LARGE)

        return request.build_absolute_uri(settings.APPAREL_DEFAULT_AVATAR_LARGE)


    @property
    def facebook_uid(self):
        """
        Try to convert username to int, if possible it is safe to assume that
        the user is a facebook-user and not an admin created user.
        """
        if not self.is_brand:
            try:
                return int(self.user.username)
            except ValueError:
                pass

        return None

    def get_friend_updates(self):
        return actstream_models.user_stream(self.user).filter(verb__in=['liked_look', 'liked_product', 'added', 'commented', 'created', 'started following', 'added_products'])

    @property
    def get_updates_last_visit(self):
        if not hasattr(self, '_updates_since_last_visit'):
            self._updates_since_last_visit = self.get_friend_updates().filter(timestamp__gt=self.updates_last_visit).count()

        return self._updates_since_last_visit

    @models.permalink
    def get_absolute_url(self):
        #if self.brand:
            #return ('profile.views.bla', [str(self.user.username)])

        return ('profile.views.likes', [str(self.slug)])
    
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

@receiver(post_save, sender=User, dispatch_uid='post_save_create_profile')
def create_profile(signal, instance, **kwargs):
    """
    Create a profile and send welcome email if a new user was created.
    """
    if kwargs['created']:
        profile, created = ApparelProfile.objects.get_or_create(user=instance)
        profile.slug = slugify(profile.display_name)
        profile.save()

@receiver(user_created_with_email, sender=User, dispatch_uid='send_welcome_mail')
def send_welcome_mail(sender, user, **kwargs):
    """
    Send welcome email on user created with email signal.
    """
    if user.email:
        subject = u'Välkommen till Apparelrow %(username)s' % {'username': user.first_name}
        body = render_to_string('profile/email_welcome.html')
        send_email_confirm_task.delay(subject, body, user.email)


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
