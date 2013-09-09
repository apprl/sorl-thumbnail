# coding=utf-8
import uuid
import os.path

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.utils.translation import get_language, ugettext_lazy as _
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.urlresolvers import reverse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError
from django.contrib.sites.models import Site

from sorl.thumbnail import get_thumbnail

from apparelrow.activity_feed.tasks import update_activity_feed
from apparelrow.apparel.utils import roundrobin
from apparelrow.profile.utils import slugify_unique, send_welcome_mail
from apparelrow.profile.tasks import mail_managers_task


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
    ('brands', 'Brands'),
    ('complete', 'Complete'),
)


class User(AbstractUser):
    name = models.CharField(max_length=100, unique=False, blank=True, null=True)
    slug = models.CharField(max_length=100, unique=True, null=True)
    image = models.ImageField(upload_to=profile_image_path, help_text=_('User profile image'), blank=True, null=True)
    about = models.TextField(_('About'), null=True, blank=True)
    language = models.CharField(_('Language'), max_length=10, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    gender = models.CharField(_('Gender'), max_length=1, choices=GENDERS, null=True, blank=True, default=None)
    blog_url = models.CharField(max_length=255, null=True, blank=True)

    # brand profile
    is_brand = models.BooleanField(default=False)
    brand = models.OneToOneField('apparel.Brand', default=None, blank=True, null=True, on_delete=models.SET_NULL, related_name='user')

    # profile login flow
    confirmation_key = models.CharField(max_length=32, null=True, blank=True, default=None)
    login_flow = models.CharField(_('Login flow'), max_length=20, choices=LOGIN_FLOW, null=False, blank=False, default='brands')

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
    facebook_user_id = models.CharField(max_length=30, default=None, unique=True, null=True, blank=True)
    facebook_access_token = models.CharField(max_length=255, null=True, blank=True)
    facebook_access_token_expire = models.DateTimeField(null=True, blank=True)

    # partner
    is_partner = models.BooleanField(default=False, blank=False, null=False, help_text=_('Partner user'))
    partner_group = models.ForeignKey('dashboard.Group', null=True, blank=True)

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

    followers_count = models.IntegerField(default=0, blank=False, null=False)
    popularity = models.DecimalField(default=0, max_digits=20, decimal_places=8, db_index=True)
    popularity_men = models.DecimalField(default=0, max_digits=20, decimal_places=8)

    class Meta:
        db_table = 'profile_user'

    def save(self, *args, **kwargs):
        for field in ['first_name', 'last_name', 'name']:
            value = getattr(self, field)
            if value:
                setattr(self, field, value.title())

        super(User, self).save(*args, **kwargs)

    @cached_property
    def blog_url_external(self):
        if not self.blog_url.startswith('http://') and not self.blog_url.startswith('https://'):
            return 'http://%s' % (self.blog_url,)

        return self.blog_url

    @cached_property
    def has_liked(self):
        """User has liked"""
        return self.product_likes.exists()

    @cached_property
    def looks(self):
        """Number of looks"""
        return self.look.filter(published=True).count()

    @cached_property
    def likes(self):
        """Number of likes on products and looks combined"""
        return self.product_likes_count + self.look_likes_count

    @cached_property
    def product_likes_count(self):
        return self.product_likes.filter(active=True).count()

    @cached_property
    def look_likes_count(self):
        return self.look_likes.filter(active=True).count()

    @cached_property
    def profile_content(self):
        # TODO: better algorithm for finding out content to fill user_medium.html templates with
        if self.is_brand and self.brand:
            products = list(self.brand.products.filter(vendorproduct__isnull=False, availability=True, published=True)[:4])
        else:
            products = list(self.product_likes.filter(active=True).order_by('-created')[:4])

        looks = list(self.look.filter(published=True).order_by('-created')[:4])

        items = []
        for item in list(roundrobin(looks, products))[:4]:
            if self.is_brand and self.brand and not hasattr(item, 'component'):
                items.append((item.get_absolute_url(), item.product_image))
            elif not self.is_brand and hasattr(item, 'product'):
                items.append((item.product.get_absolute_url(), item.product.product_image))
            elif hasattr(item, 'component'):
                items.append((item.get_absolute_url(), item.static_image))

        if len(items) < 4:
            for _ in xrange(4 - len(items)):
                items.append((False, False))

        return items

    @cached_property
    def display_name(self):
        return self.display_name_live

    @property
    def display_name_live(self):
        if self.name:
            return self.name

        if self.first_name:
            return u'%s %s' % (self.first_name, self.last_name)

        return self.username

    @cached_property
    def avatar_small(self):
        if self.image:
            return get_thumbnail(self.image, '32x32', crop='center').url

        if self.facebook_user_id:
            return 'http://graph.facebook.com/%s/picture?width=32&height=32' % self.facebook_user_id

        if self.is_brand:
            return staticfiles_storage.url(settings.APPAREL_DEFAULT_BRAND_AVATAR)

        return staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR)

    @cached_property
    def avatar(self):
        if self.image:
            return get_thumbnail(self.image, '50x50', crop='center').url

        if self.facebook_user_id:
            return 'http://graph.facebook.com/%s/picture?type=square' % self.facebook_user_id

        if self.is_brand:
            return staticfiles_storage.url(settings.APPAREL_DEFAULT_BRAND_AVATAR)

        return staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR)

    @cached_property
    def avatar_medium(self):
        if self.image:
            return get_thumbnail(self.image, '125').url

        if self.facebook_user_id:
            return 'http://graph.facebook.com/%s/picture?type=normal' % self.facebook_user_id

        if self.is_brand:
            return staticfiles_storage.url(settings.APPAREL_DEFAULT_BRAND_AVATAR_MEDIUM)

        return staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_MEDIUM)

    @cached_property
    def avatar_large(self):
        if self.image:
            return get_thumbnail(self.image, '208').url

        if self.facebook_user_id:
            return 'http://graph.facebook.com/%s/picture?width=208' % self.facebook_user_id

        if self.is_brand:
            return staticfiles_storage.url(settings.APPAREL_DEFAULT_BRAND_AVATAR_LARGE)

        return staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE)

    def avatar_large_absolute_uri(self, request):
        if self.image:
            return request.build_absolute_uri(get_thumbnail(self.image, '208').url)

        if self.facebook_user_id:
            return 'http://graph.facebook.com/%s/picture?width=208' % self.facebook_user_id

        if self.is_brand:
            return request.build_absolute_uri(staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE))

        return request.build_absolute_uri(staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE))

    @cached_property
    def url_likes(self):
        if self.is_brand:
            return reverse('brand-likes', args=[self.slug])

        return reverse('profile-likes', args=[self.slug])

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
        # TODO: might need to check brand field for null values
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    token = models.CharField(max_length=42)
    email = models.CharField(max_length=256)

    def __unicode__(self):
        return '%s - %s' % (self.user, self.email)

#
# Update slug and send welcome email when a new user is created
#

@receiver(post_save, sender=User, dispatch_uid='post_save_user_create')
def post_save_user_create(signal, instance, **kwargs):
    """
    Update slug and send welcome email if a new user was created.
    """
    if kwargs['created']:
        # Send welcome email if facebook user and has email
        if instance.email and instance.facebook_user_id:
            send_welcome_mail(instance)

        if not instance.slug:
            instance.slug = slugify_unique(instance.display_name_live, instance.__class__)
            instance.save()

        mail_subject = 'New user signup: %s' % (instance.display_name_live,)
        if not instance.facebook_user_id:
            mail_subject = 'New email user signup: %s' % (instance.display_name_live,)

        site_object = Site.objects.get_current()
        mail_url = 'http://%s%s' % (site_object.domain, instance.get_absolute_url())

        mail_managers_task.delay(mail_subject, 'URL: %s' % (mail_url,))


@receiver(user_logged_in, sender=User, dispatch_uid='update_language_on_login')
def update_profile_language(sender, user, request, **kwargs):
    language = get_language()
    if user.is_authenticated() and language is not None:
        user.language = language
        user.save()


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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='following', on_delete=models.CASCADE)
    user_follow = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='followers', on_delete=models.CASCADE)
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



import apparelrow.profile.activity
