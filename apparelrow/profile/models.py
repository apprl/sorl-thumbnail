# coding=utf-8
import uuid
import os.path

from django.db import models
from django.db.models import get_model
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from apparelrow.activity_feed.models import Activity
from django.contrib.auth.models import AbstractUser
from django.utils.translation import get_language, ugettext_lazy as _
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.urlresolvers import reverse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError
from django.contrib.sites.models import Site
from sorl.thumbnail import get_thumbnail, default

from apparelrow.profile.notifications import process_follow_user
from apparelrow.activity_feed.tasks import update_activity_feed
from apparelrow.apparel.utils import roundrobin
from apparelrow.apparel.sorl_extension import CustomCircularEngine
from apparelrow.apparel.utils import get_paged_result
from apparelrow.profile.utils import slugify_unique, send_welcome_mail
from apparelrow.profile.tasks import mail_managers_task
from django.utils import timezone

EVENT_CHOICES = (
    ('A', _('All')),
    ('F', _('Those I follow')),
    ('N', _('No one')),
)

NOTIFICATION_CHOICES = (
    ('I'), _('Immediately'),
    ('D', _('Daily')),
    ('W', _('Weekly')),
    ('N', _('Never')),
)

SUMMARY_CHOICES = (
    ('D', _('Daily')),
    ('W', _('Weekly')),
    ('N', _('Never')),
)

FB_FRIEND_CHOICES = (
    ('A', _('Yes')),
    ('N', _('No')),
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
    manual_about = models.TextField(_('Manual About'), null=True, blank=True)
    language = models.CharField(_('Language'), max_length=10, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    gender = models.CharField(_('Gender'), max_length=1, choices=GENDERS, null=True, blank=True, default=None)
    blog_url = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(_('Location'), null=True, blank=True, max_length=10, choices=settings.LOCATION_MAPPING)

    is_hidden = models.BooleanField(default=False, blank=False, null=False)

    # brand profile
    is_brand = models.BooleanField(default=False)
    brand = models.OneToOneField('apparel.Brand', default=None, blank=True, null=True, on_delete=models.SET_NULL, related_name='user')

    # profile login flow
    confirmation_key = models.CharField(max_length=32, null=True, blank=True, default=None)
    # XXX: disabled brands from the login flow
    login_flow = models.CharField(_('Login flow'), max_length=20, choices=LOGIN_FLOW, null=False, blank=False, default='complete')

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
    is_top_partner = models.BooleanField(default=False, blank=False, null=False, help_text=_('Top partner user'))
    partner_group = models.ForeignKey('dashboard.Group', verbose_name=_('Commission group'), null=True, blank=True)

    # referral partner
    referral_partner = models.BooleanField(default=False, blank=False, null=False, help_text=_('Referral partner user'))
    referral_partner_code = models.CharField(max_length=16, blank=True, null=True)
    referral_partner_parent = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)
    referral_partner_parent_date = models.DateTimeField(null=True, blank=True)

    # publisher network
    owner_network = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name='publisher_network', verbose_name=_("Belongs to Publisher Network"), help_text="Assign publisher to another user's Publisher Network.")

    # for publisher network owners
    is_subscriber = models.BooleanField(default=False, null=False, blank=False)
    owner_network_cut = models.DecimalField(null=True, blank=True, default='1.00', max_digits=10, decimal_places=3, verbose_name=_("Owner's cut"),
                                    help_text="If this user is owner of a publisher network, set the owner's cut. Between 0 and 1, determines the percentage that the user will receive from every sale in the network (1 equals 100%)")

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
    facebook_friends = models.CharField(max_length=1, choices=FB_FRIEND_CHOICES, default='A',
            help_text=_('When a Facebook friend has joined Apprl'))
    summary_mails = models.CharField(max_length=1, choices=SUMMARY_CHOICES, default='W',
            help_text=_('The latest updates on Apprl for you'))
    product_like_summaries = models.CharField(max_length=1, choices=SUMMARY_CHOICES, default='D',
            help_text=_('When someone likes the same product as you'))
    look_like_summaries = models.CharField(max_length=1, choices=SUMMARY_CHOICES, default='D',
            help_text=_('When someone likes the same look as you'))
    earning_summaries = models.CharField(max_length=1, choices=SUMMARY_CHOICES, default='D',
            help_text=_('When you have earned money'))
    friend_summaries = models.CharField(max_length=1, choices=SUMMARY_CHOICES, default='W',
            help_text=_('Summary with the latest from the people I follow'))
    brand_summaries = models.CharField(max_length=1, choices=SUMMARY_CHOICES, default='W',
            help_text=_('Summary with the latest from the brands I follow'))
    follow_recommendations = models.CharField(max_length=1, choices=SUMMARY_CHOICES, default='W',
            help_text=_('Recommendations for who to follow'))

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
    def translated_manual_about(self):
        return getattr(self, 'manual_about_%s' % (get_language(),), None)

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
    def shops(self):
        """Number of shops"""
        return self.shop.all().count()

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
    def total_look_count(self):
        return self.look_likes_count + self.looks

    @cached_property
    def notifications(self):
        notifications = self.notification_events.order_by('created').reverse()
        paged_result = get_paged_result(notifications, 10, 1)
        return paged_result

    @cached_property
    def unread_count(self):
        return self.notification_events.filter(seen=False).count()

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
    def avatar_circular(self):
        """ Small size circular avatar using CustomCircularEngine """
        if self.image:
            old_engine = default.engine
            default.engine = CustomCircularEngine()
            image = get_thumbnail(self.image, '50x50', format="PNG").url
            default.engine = old_engine
            return image

    @cached_property
    def avatar_circular_medium(self):
        """ Medium size circular avatar using CustomCircularEngine """
        if self.image:
            old_engine = default.engine
            default.engine = CustomCircularEngine()
            image = get_thumbnail(self.image, '125', format="PNG").url
            default.engine = old_engine
            return image

    @cached_property
    def avatar_circular_large(self):
        """ Large size circular avatar using CustomCircularEngine """
        if self.image:
            old_engine = default.engine
            default.engine = CustomCircularEngine()
            image = get_thumbnail(self.image, '208', format="PNG").url
            default.engine = old_engine
            return image

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
    def url_likedlooks(self):
        return reverse('profile-likedlooks', args=[self.slug])

    @cached_property
    def url_brandlooks(self):
        return reverse('profile-brandlooks', args=[self.slug])

    @cached_property
    def url_shops(self):
        return reverse('profile-shops', args=[self.slug])

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

    def has_partner_group_ownership(self):
        return get_model('dashboard', 'Group').objects.filter(owner=self).exists()


    def is_referral_parent_valid(self):
        if self.referral_partner_parent and self.referral_partner_parent_date and self.referral_partner_parent_date > timezone.now():
            return True

        return False

    def get_referral_domain_url(self):
        if self.referral_partner and self.referral_partner_code:
            site_object = Site.objects.get_current()
            return 'http://%s%s' % (site_object.domain, self.get_referral_url())

        return None

    def get_referral_url(self):
        if self.referral_partner and self.referral_partner_code:
            return reverse('dashboard-referral-signup', args=[self.referral_partner_code])

        return None

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
    notes = models.TextField(_('Notes'), null=True, blank=True)

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
        return [follow.user for follow in self.filter(user_follow__is_hidden=False, user_follow=profile, active=True).select_related('user')]

    def following(self, profile):
        return [follow.user_follow for follow in self.filter(user__is_hidden=False, user=profile, active=True).prefetch_related('user_follow')]

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

class NotificationManager(models.Manager):
     def push_notification(self, owner, type, actor=None, product=None, look=None):
        if actor.is_hidden:
            # Don't push notifications for hidden users
            return None
        event = self.get_or_create(owner=owner,
                                    actor=actor,
                                    type=type,
                                    product=product,
                                    look=look)[0]
        event.save()

class NotificationEvent(models.Model):
    """
    Create an event whenever something relevant happens, to later display for user or build summaries
    """
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True, related_name='notification_events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='performed_events', blank=True, null=True)
    look = models.ForeignKey('apparel.Look', related_name='notifications', on_delete=models.CASCADE, blank=True, null=True)
    product = models.ForeignKey('apparel.Product', related_name='notifications', on_delete=models.CASCADE, blank=True, null=True)
    seen = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)

    created = models.DateTimeField(_('Time created'), auto_now_add=True, null=True, blank=True)

    #add custom manager
    objects = NotificationManager()

    sale_new_price = models.IntegerField(blank=True, null=True)
    sale_old_price = models.IntegerField(blank=True, null=True)
    sale_currency = models.CharField(max_length=10, unique=False, blank=True, null=True)

    TYPES =   (
        ("FB", "fbFriend"),
        ("SALE", "itemSale"),
        ("FOLLOW", "newFollower"),
        ("LIKELOOK", "likedLook"),
        ("COMMLOOK", "commentedLook"),
        ("NEWLOOK", "createdLook"),
        ("PURCH", "generatedPurchase"),
    )

    type = models.CharField(max_length=15, choices=TYPES)



    @cached_property
    def from_today(self):
        ref_time = timezone.now()
        return ref_time.date() == self.created.date()

#
# Follow handlers
#

@receiver(post_save, sender=Follow, dispatch_uid='profile.models.on_follow')
def on_follow(signal, instance, **kwargs):
    """
    Update activities on follow update.
    """
    update_activity_feed.delay(instance.user, instance.user_follow, instance.active)


@receiver(post_save, sender=Follow, dispatch_uid='profile.activity.post_save_follow_handler')
def post_save_follow_handler(sender, instance, **kwargs):
    """
    Post save handler for follow objects. Updates followers count on user
    profile and attempts to notify users about this new follow object.
    """
    apparel_profile = instance.user_follow
    if instance.active and not instance.user.is_hidden:
        apparel_profile.followers_count = apparel_profile.followers_count + 1
        process_follow_user.delay(instance.user_follow, instance.user, instance)
        Activity.objects.push_activity(instance.user, 'follow', instance.user_follow, instance.user.gender)
        NotificationEvent.objects.push_notification(instance.user_follow, "FOLLOW", instance.user)
        apparel_profile.save()
    elif not instance.user.is_hidden:
        apparel_profile.followers_count = apparel_profile.followers_count - 1
        Activity.objects.pull_activity(instance.user, 'follow', instance.user_follow)
        apparel_profile.save()

@receiver(pre_delete, sender=Follow, dispatch_uid='profile.activity.pre_delete_follow_handler')
def pre_delete_follow_handler(sender, instance, **kwargs):
    """
    Pre delete handler for follow objects. Updates followers count on user
    profile.
    """
    if instance.user_follow:
        instance.user_follow.followers_count = instance.user_follow.followers_count - 1
        instance.user_follow.save()

    if instance.user and instance.user_follow:
        Activity.objects.pull_activity(instance.user, 'follow', instance.user_follow)


#
# NOTIFICATION CACHE
#

class NotificationCache(models.Model):
    key = models.CharField(max_length=255, unique=True, blank=False, null=False)

    def __unicode__(self):
        return '%s' % (self.key,)
