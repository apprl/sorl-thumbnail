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
from django.contrib.auth.signals import user_logged_in
from django.core.urlresolvers import reverse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError

from sorl.thumbnail import get_thumbnail
from django_extensions.db.fields import AutoSlugField

from activity_feed.tasks import update_activity_feed
from profile.tasks import send_email_confirm_task
from profile.signals import user_created_with_email
from profile.utils import slugify_unique

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
    ('bio', 'Bio'),
    ('friends', 'Friends'),
    ('featured', 'Featured'),
    ('brands', 'Brands'),
    ('like', 'Like'),
    ('complete', 'Complete'),
)

class ApparelProfile(models.Model):
    """Every user is mapped against an ApparelProfile"""
    user = models.OneToOneField(User, related_name='profile')

    name                = models.CharField(max_length=100, unique=False, blank=True, null=True)
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
    login_flow = models.CharField(_('Login flow'), max_length=20, choices=LOGIN_FLOW, null=False, blank=False, default='bio')

    # newsletter settings
    newsletter = models.BooleanField(default=True, blank=False, null=False, help_text=_('Participating in newsletter'))

    # discount notification setting
    discount_notification = models.BooleanField(default=True, blank=False, null=False, help_text=_('Receiving sale alerts'))

    # share settings
    fb_share_like_product = models.BooleanField(default=True, blank=False, null=False)
    fb_share_like_look = models.BooleanField(default=True, blank=False, null=False)
    fb_share_follow_profile = models.BooleanField(default=True, blank=False, null=False)
    fb_share_create_look = models.BooleanField(default=True, blank=False, null=False)

    # facebook
    facebook_access_token = models.CharField(max_length=255, null=True, blank=True)
    facebook_access_token_expire = models.DateTimeField(null=True, blank=True)

    # partner
    is_partner = models.BooleanField(default=False, blank=False, null=False, help_text=_('Partner user'))
    partner_group = models.ForeignKey('dashboard.Group', null=True, blank=True)
    blog_url = models.CharField(max_length=255, null=True, blank=True)

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
    facebook_friends = models.CharField(max_length=1, choices=EVENT_CHOICES, default='A',
            help_text=_('When a Facebook friend has joined Apprl'))

    first_visit = models.BooleanField(default=True, blank=False, null=False,
            help_text=_('Is this the first visit?'))

    followers_count = models.IntegerField(default=0, blank=False, null=False)

    popularity    = models.DecimalField(default=0, max_digits=20, decimal_places=8, db_index=True)

    @cached_property
    def blog_url_external(self):
        if not self.blog_url.startswith('http'):
            return 'http://%s' % (self.blog_url,)

        return self.blog_url

    @models.permalink
    def get_looks_url(self):
        return ('looks_by_user', [str(self.user.username)])

    # XXX: make this a real column on the model?
    @cached_property
    def has_liked(self):
        """User has liked"""
        return self.user.product_likes.exists()

    @cached_property
    def looks(self):
        """Number of looks"""
        return self.user.look.filter(published=True).count()

    @cached_property
    def likes(self):
        """Number of likes on products and looks combined"""
        return self.product_likes_count + self.look_likes_count

    @cached_property
    def product_likes_count(self):
        return self.user.product_likes.filter(active=True).count()

    @cached_property
    def look_likes_count(self):
        return self.user.look_likes.filter(active=True).count()

    @cached_property
    def display_name(self):
        return self.display_name_live

    @property
    def display_name_live(self):
        if self.name is not None:
            return self.name

        if self.user.first_name:
            return u'%s %s' % (self.user.first_name, self.user.last_name)

        return u'%s' % (self.user,)

    @cached_property
    def avatar_small(self):
        if self.image:
            return get_thumbnail(self.image, '32x32', crop='center').url

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?width=32&height=32' % self.facebook_uid

        if self.is_brand:
            return staticfiles_storage.url(settings.APPAREL_DEFAULT_BRAND_AVATAR)

        return staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR)

    @cached_property
    def avatar(self):
        if self.image:
            return get_thumbnail(self.image, '50x50', crop='center').url

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?type=square' % self.facebook_uid

        if self.is_brand:
            return staticfiles_storage.url(settings.APPAREL_DEFAULT_BRAND_AVATAR)

        return staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR)

    @cached_property
    def avatar_medium(self):
        if self.image:
            return get_thumbnail(self.image, '125').url

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?type=normal' % self.facebook_uid

        if self.is_brand:
            return staticfiles_storage.url(settings.APPAREL_DEFAULT_BRAND_AVATAR_MEDIUM)

        return staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR)

    @cached_property
    def avatar_large(self):
        if self.image:
            return get_thumbnail(self.image, '208').url

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?width=208' % self.facebook_uid

        if self.is_brand:
            return staticfiles_storage.url(settings.APPAREL_DEFAULT_BRAND_AVATAR_LARGE)

        return staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)

    def avatar_large_absolute_uri(self, request):
        if self.image:
            return request.build_absolute_uri(get_thumbnail(self.image, '208').url)

        if self.facebook_uid:
            return 'http://graph.facebook.com/%s/picture?width=208' % self.facebook_uid

        if self.is_brand:
            return request.build_absolute_uri(staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE))

        return request.build_absolute_uri(staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE))


    @cached_property
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

    @cached_property
    def url_likes(self):
        if self.is_brand:
            return reverse('brand-likes', args=[self.slug])

        return reverse('profile-likes', args=[self.slug])

    @cached_property
    def url_updates(self):
        if self.is_brand:
            return reverse('brand-updates', args=[self.slug])

        return reverse('profile-updates', args=[self.slug])

    @cached_property
    def url_looks(self):
        if self.is_brand:
            return reverse('brand-looks', args=[self.slug])

        return reverse('profile-looks', args=[self.slug])
    @cached_property
    def url_followers(self):
        if self.is_brand:
            return reverse('brand-followers', args=[self.slug])

        return reverse('profile-followers', args=[self.slug])
    @cached_property
    def url_following(self):
        if self.is_brand:
            return reverse('brand-following', args=[self.slug])

        return reverse('profile-following', args=[self.slug])

    @models.permalink
    def get_absolute_url(self):
        if self.is_brand:
            return ('brand-likes', [str(self.slug)])

        return ('profile-likes', [str(self.slug)])

    def clean(self):
        """
        Validate custom constraints
        """
        if self.is_partner and self.partner_group is None:
            raise ValidationError(_(u'Partner group must be set to be able to set partner status'))

    def __unicode__(self):
        return self.display_name


class PaymentDetail(models.Model):
    user = models.ForeignKey('auth.User')
    name = models.CharField(max_length=128)
    company = models.BooleanField(default=False, null=False, blank=False, choices=((True, _('Receive payments as a company')), (False, _('Receive payments as a private person'))))
    orgnr = models.CharField(max_length=32, null=True, blank=True)
    banknr = models.CharField(max_length=32, null=True, blank=True)
    clearingnr = models.CharField(max_length=32, null=True, blank=True)
    address = models.CharField(_('Address'), max_length=64, null=True, blank=True)
    postal_code = models.CharField(_('Postal code'), max_length=8, null=True, blank=True)
    city = models.CharField(_('City'), max_length=64, null=True, blank=True)


    def __unicode__(self):
        return '%s - %s' % (self.user, self.name)


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
        profile.slug = slugify_unique(profile.display_name_live, profile.__class__)
        profile.save()

@receiver(user_created_with_email, sender=User, dispatch_uid='send_welcome_mail')
def send_welcome_mail(sender, user, **kwargs):
    """
    Send welcome email on user created with email signal.
    """
    if user.email:
        subject = _(u'Welcome to Apprl %(username)s') % {'username': user.first_name}
        body = render_to_string('profile/email_welcome.html', {'first_name': user.first_name})
        send_email_confirm_task.delay(subject, body, user.email)

@receiver(user_logged_in, sender=User, dispatch_uid='update_language_on_login')
def update_profile_language(sender, user, request, **kwargs):
    language = get_language()
    if user.is_authenticated() and language is not None:
        profile = user.get_profile()
        profile.language = language
        profile.save()

#def delete_user_comments(signal, instance, **kwargs):
    #"""
    #This signal attemps to delete any comments which is written by the user.
    #"""
    #Comment.objects.filter(user=instance).delete()
#post_delete.connect(delete_user_comments, sender=User)


#
# FOLLOWS
#

class FollowManager(models.Manager):

    def followers(self, profile):
        return [follow.user for follow in self.filter(user_follow=profile, active=True).select_related('user')]

    def following(self, profile):
        return [follow.user_follow for follow in self.filter(user=profile, active=True).prefetch_related('user_follow')]

# TODO: when django 1.5 is released we will only use one profile/user class
class Follow(models.Model):
    """
    Follow model lets a user follow another user.
    """
    user = models.ForeignKey(ApparelProfile, related_name='following', on_delete=models.CASCADE)
    user_follow = models.ForeignKey(ApparelProfile, related_name='followers', on_delete=models.CASCADE)
    created = models.DateTimeField(_('Time created'), auto_now_add=True, null=True, blank=True)
    modified = models.DateTimeField(_('Time modified'), auto_now=True, null=True, blank=True)
    active = models.BooleanField(default=True, db_index=True)

    objects = FollowManager()

    def __unicode__(self):
        return u'%s follows %s' % (self.user, self.user_follow)

    class Meta:
        unique_together = ('user', 'user_follow')

@receiver(post_save, sender=Follow, dispatch_uid='profile.models.on_follow')
def on_follow(signal, instance, **kwargs):
    """
    Update activities on follow update.
    """
    update_activity_feed.delay(instance.user, instance.user_follow, instance.active)


#
# NOTIFICATION CACHE
#

class NotificationCache(models.Model):
    key = models.CharField(max_length=255, unique=True, blank=False, null=False)

    def __unicode__(self):
        return '%s' % (self.key,)



import profile.activity
