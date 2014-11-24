import logging
import uuid
import os.path
import decimal
import datetime

from django.db import models
from django.db.models import Sum, Min
from django.db.models.loading import get_model
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import get_language, ugettext_lazy as _
from django.template.defaultfilters import slugify
from django.conf import settings
from django.forms import ValidationError
from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.functional import cached_property

from apparelrow.apparel.signals import look_saved
from apparelrow.apparel.manager import ProductManager, LookManager
from apparelrow.apparel.cache import invalidate_model_handler
from apparelrow.apparel.utils import currency_exchange, get_brand_and_category
from apparelrow.apparel.base_62_converter import saturate, dehydrate
from apparelrow.apparel.tasks import build_static_look_image, empty_embed_look_cache

from apparelrow.profile.notifications import process_sale_alert

import requests

from tagging.fields import TagField
from sorl.thumbnail import ImageField, get_thumbnail
from django_extensions.db.fields import AutoSlugField
from mptt.models import MPTTModel, TreeForeignKey
from mptt.managers import TreeManager


PRODUCT_GENDERS = (
    ('W', 'Women',),
    ('M', 'Men',),
    ('U', 'Unisex',),
)

LOOK_COMPONENT_TYPES = (
    ('C', 'Collage'),
    ('P', 'Picture'),
)

LOOK_COMPONENT_POSITIONED = (
    ('A', 'Automatically'),
    ('M', 'Manually'),
)


logger = logging.getLogger('apparel.debug')


#
# Brand
#

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    old_name = models.CharField(max_length=100, null=True, blank=True)
    last_update = models.DateTimeField(_("Last update"), null=True, blank=True)

    def __unicode__(self):
        return u'%s' % self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'

    class Exporter:
        export_fields = ['__all__']

@receiver(post_save, sender=Brand, dispatch_uid='brand_create_user')
def brand_create_user(sender, instance, **kwargs):
    if 'created' in kwargs and kwargs['created']:
        user, created = get_user_model().objects.get_or_create(username=u'brand-%s' % (instance.id,))
        if created:
            user.name = instance.name
            user.slug = slugify(user.name)
            user.brand = instance
            user.is_brand = True
            user.save()


#
# Option
#

class OptionType(MPTTModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

    objects = tree = TreeManager()

    def __unicode__(self):
        return u"%s" % self.name

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        ordering = ['name']
        verbose_name = _("Option Type")
        verbose_name_plural = _("Option Types")

# XXX: force translations of colors
_('Black')
_('Grey')
_('White')
_('Beige')
_('Brown')
_('Red')
_('Yellow')
_('Green')
_('Blue')
_('Silver')
_('Gold')
_('Pink')
_('Orange')
_('Magenta')
_('Purple')

class Option(models.Model):
    value       = models.CharField(_('Option value'), max_length=255)
    option_type = models.ForeignKey(OptionType)

    def __unicode__(self):
        return u"%s: %s" % (self.option_type.name, self.value)

    class Meta:
        ordering = ['option_type']
        unique_together     = (('option_type', 'value'),)
        verbose_name        = _('Option Item')
        verbose_name_plural = _('Option Items')

    class Exporter:
        export_fields = ['__all__', '-active']


#
# Vendor
#

class Vendor(models.Model):
    name     = models.CharField(max_length=100, db_index=True)
    homepage = models.URLField(_('Home page'))
    logotype = models.ImageField(upload_to=settings.APPAREL_LOGO_IMAGE_ROOT, help_text=_('Logotype'), max_length=127, blank=True, null=True)
    user     = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', blank=True, null=True)
    provider = models.CharField(max_length=50)

    class Meta:
        ordering = ['name']
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __unicode__(self):
        return u"%s" % self.name


#
# Category
#

class Category(MPTTModel):
    name          = models.CharField(max_length=100, db_index=True)
    name_order    = models.CharField(max_length=100)
    singular_name = models.CharField(max_length=100, null=True, blank=True, default='')
    parent        = TreeForeignKey('self', null=True, blank=True, related_name='children')
    active        = models.BooleanField(default=False, help_text=_('Only active categories are visible and searchable on the website'), db_index=True)
    option_types  = models.ManyToManyField(OptionType, blank=True, verbose_name=_('Option types'))
    on_front_page = models.BooleanField(default=False, help_text=_('The category is visible on the front page'), db_index=True)

    objects = tree = TreeManager()

    def save(self, *args, **kwargs):
        # FIXME: Can you get Django to auto truncate fields?
        self.name = self.name[:100]
        super(Category, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%s" % self.name

    class Exporter:
        export_fields = ['name', 'name_order', 'option_types']

    class Meta:
        ordering = ('tree_id', 'lft')
        verbose_name_plural = 'categories'

    class MPTTMeta:
        order_insertion_by = ['name_order']

models.signals.post_save.connect(invalidate_model_handler, sender=Category)
models.signals.post_delete.connect(invalidate_model_handler, sender=Category)


#
# Product
#

class Product(models.Model):
    manufacturer = models.ForeignKey(Brand, related_name='products', blank=True, null=True, on_delete=models.SET_NULL)
    static_brand = models.CharField(max_length=100, default='')
    category = TreeForeignKey(Category, blank=True, null=True)
    options  = models.ManyToManyField(Option,   blank=True, verbose_name=_("Option"))
    slug = AutoSlugField(_("Slug Name"), populate_from=("static_brand", "product_name",), blank=True,
        help_text=_("Ued for URLs, auto-generated from name if blank"), max_length=80)
    sku = models.CharField(_("Stock Keeping Unit"), max_length=255, blank=False, null=False,
        help_text=_("Has to be unique with the static_brand"))
    product_name  = models.CharField(max_length=200, null=True, blank=True)
    date_added    = models.DateTimeField(_("Time added"), null=True, blank=True, db_index=True)
    date_published= models.DateTimeField(_("Time published"), null=True, blank=True)
    modified      = models.DateTimeField(_("Time modified"), null=True, auto_now=True)
    description   = models.TextField(_('Product description'), null=True, blank=True)
    product_image = ImageField(upload_to=settings.APPAREL_PRODUCT_IMAGE_ROOT, max_length=255, help_text=_('Product image'))
    vendors       = models.ManyToManyField(Vendor, through='VendorProduct')
    # FIXME: Could we have ForeignKey to VendorProduct instead?
    gender        = models.CharField(_('Gender'), max_length=1, choices=PRODUCT_GENDERS, null=True, blank=True, db_index=True)
    feed_gender   = models.CharField(_('Feed gender'), max_length=1, choices=PRODUCT_GENDERS, null=True, blank=True, db_index=True)
    published     = models.BooleanField(default=False, db_index=True)
    popularity    = models.DecimalField(default=0, max_digits=20, decimal_places=8, db_index=True)
    availability  = models.BooleanField(_('In stock'), null=False, blank=False, default=False)

    objects = models.Manager()
    valid_objects = ProductManager(availability=True)
    published_objects = ProductManager(availability=False)

    @cached_property
    def score(self):
        return self.likes.filter(active=True).count()

    @cached_property
    def comment_count(self):
        return Comment.objects.for_model(self).filter(is_removed=False, is_public=True).count()

    @cached_property
    def default_vendor(self):
        try:
            return self.vendorproduct.order_by('price').select_related('vendor')[0]
        except IndexError:
            pass

        return None

    @cached_property
    def default_vendor_price(self):
        if self.default_vendor.locale_discount_price:
            return self.default_vendor.locale_discount_price

        return self.default_vendor.locale_price

    @cached_property
    def original_currency_list(self):
        locale = get_language()
        currency = settings.LANGUAGE_TO_CURRENCY.get(locale, settings.APPAREL_BASE_CURRENCY)

        original_currency = []
        for vendorproduct in self.vendorproduct.all():
            if vendorproduct.original_currency != currency:
                original_currency.append(vendorproduct.original_currency)

        return original_currency

    @models.permalink
    def get_absolute_url(self):
        return ('product-detail', [str(self.slug)])

    @cached_property
    def categories_all_languages(self):
        current_category = self.category
        categories = []
        while current_category:
            if current_category.name_sv:
                categories.insert(0, current_category.name_sv)
            if current_category.name_en:
                categories.insert(0, current_category.name_en)
            current_category = current_category.parent

        return categories

    @cached_property
    def _colors(self):
        return self.options.filter(option_type__name='color').values_list('pk', 'value')

    @cached_property
    def colors(self):
        temp_colors = self._colors
        if temp_colors:
            return zip(*self._colors)[1]

        return []

    @cached_property
    def colors_pk(self):
        temp_colors = self._colors
        if temp_colors:
            return zip(*self._colors)[0]

        return []

    @cached_property
    def color_list_locale(self):
        if not hasattr(self, '_color_list_locale'):
            self._color_list_locale = [unicode(_(o.title())) for o in self.colors]

        return self._color_list_locale

    @cached_property
    def alt_text(self):
        return u'%s %s %s' % (self.manufacturer, self.product_name, (', '.join(self.color_list_locale)))

    @cached_property
    def categories(self):
        c = self.category
        categories = []

        while c:
            categories.insert(0, c)
            c = c.parent

        return categories

    def save(self, *args, **kwargs):
        if not self.pk:
            self.date_added = datetime.datetime.now()

        if not self.sku:
            self.sku = self.slug

        if not self.gender:
            try:
                self.gender = self.vendorproduct.get().vendor_category.default_gender
            except:
                pass

        if self.category and self.manufacturer and self.gender and self.product_image:
            self.published = True
        else:
            self.published = False

        # If no published date and published is true we mark this date as the published date
        if not self.date_published and self.published == True:
            self.date_published = datetime.datetime.now()

        super(Product, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%s %s" % (self.manufacturer, self.product_name)

    class Meta:
        ordering = ('-id',)
        unique_together = (('static_brand', 'sku'),)

    class Exporter:
        export_fields = ['__all__', 'get_absolute_url', 'default_vendor', 'score']

models.signals.post_save.connect(invalidate_model_handler, sender=Product)
models.signals.post_delete.connect(invalidate_model_handler, sender=Product)

@receiver(post_save, sender=Product, dispatch_uid='product_update_activity_post_save')
def product_update_activity_post_save(sender, instance, **kwargs):
    # TODO: this might solve deadlock in database (stupid mysql)
    content_type = ContentType.objects.get_for_model(instance)
    get_model('activity_feed', 'activity').objects.filter(content_type=content_type, object_id=instance.pk).update(is_available=instance.availability)
    #get_model('activity_feed', 'activity').objects.update_activity(instance)


#
# ProductLike
#

class ProductLike(models.Model):
    """
    Keep track of likes on products
    """
    product = models.ForeignKey(Product, related_name='likes', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='product_likes')
    created = models.DateTimeField(_("Time created"), auto_now_add=True, null=True, blank=True)
    modified = models.DateTimeField(_("Time modified"), auto_now=True, null=True, blank=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return u'%s likes product %s' % (self.user, self.product)

    class Meta:
        unique_together = (('product', 'user'),)

models.signals.post_save.connect(invalidate_model_handler, sender=ProductLike)
models.signals.post_delete.connect(invalidate_model_handler, sender=ProductLike)

@receiver(post_save, sender=ProductLike, dispatch_uid='product_like_post_save')
def product_like_post_save(sender, instance, **kwargs):
    if not hasattr(instance, 'user'):
        logging.warning('Trying to register an activity, but %s has not user attribute' % instance)
        return

    if instance.active == True:
        get_model('activity_feed', 'activity').objects.push_activity(instance.user, 'like_product', instance.product, instance.product.gender)
    else:
        get_model('activity_feed', 'activity').objects.pull_activity(instance.user, 'like_product', instance.product)

@receiver(pre_delete, sender=ProductLike, dispatch_uid='product_like_pre_delete')
def product_like_pre_delete(sender, instance, **kwargs):
    if not hasattr(instance, 'user'):
        logging.warning('Trying to remove an activity, but %s has not user attribute' % instance)
        return

    get_model('activity_feed', 'activity').objects.pull_activity(instance.user, 'like_product', instance.product)


#
# ShortStoreLink and ShortProductLink
#

SHORT_CONSTANT = 999999

class ShortStoreLinkManager(models.Manager):
    def get_for_short_link(self, short_link, user_id=None):
        instance = ShortStoreLink.objects.get(pk=(saturate(short_link) - SHORT_CONSTANT))

        if user_id is None:
            user_id = 0

        return instance.template.format(sid='{}-0-Ext-Store'.format(user_id)), instance.vendor.name


class ShortStoreLink(models.Model):
    vendor   = models.ForeignKey(Vendor)
    template = models.CharField(max_length=512, blank=False, null=False, help_text="""Use {sid} in the URL where you want the sid string to be placed<br><br>
            AAN<br>http://apprl.com/a/link/?store_id=STORE_ID&custom={sid}&url=DESTINATION_URL<br><br>
            Tradedoubler<br>http://clk.tradedoubler.com/click?p=PROGRAM_ID&a= 1853028&g=xxxxx&epi={sid}&url=DESTINATION_URL<br><br>
            Linkshare<br>http://click.linksynergy.com/fs-bin/click?id=xxxx&offerid=xxxx&type=xxxx&tmpid=xxxx&u1={sid}&RD_PARM1=DESTINATION_URL<br><br>
            CJ<br>http://www.anrdoezrs.net/links/4125005/sid/{sid}/DESTINATION_URL<br><br>
            AW<br>http://www.awin1.com/cread.php?awinmid=xxxx&awinaffid=xxxxx&clickref={sid}&p=DESTINATION_URL<br><br>
            Zanox<br>http://ad.zanox.com/ppc/?xxxxx&zpar0=[[{sid}]]&ulp=[[DESTINATION_URL]]""")

    objects = ShortStoreLinkManager()

    def link(self):
        return dehydrate(self.pk + SHORT_CONSTANT)


class DomainDeepLinking(models.Model):
    vendor = models.ForeignKey(Vendor)
    domain = models.CharField(max_length=100, blank=False, null=False)
    template = models.CharField(max_length=512, blank=False, null=False)


class ShortDomainLinkManager(models.Manager):
    def get_short_domain_for_link(self, short_link):
        instance = ShortDomainLink.objects.get(pk=(saturate(short_link) - SHORT_CONSTANT))

        return instance.url, instance.vendor.name, instance.user.pk


class ShortDomainLink(models.Model):
    url = models.CharField(max_length=512, blank=False, null=False)
    vendor = models.ForeignKey(Vendor)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='short_domain_links')
    created = models.DateTimeField(default=timezone.now)

    objects = ShortDomainLinkManager()

    def link(self):
        return dehydrate(self.pk + SHORT_CONSTANT)

    class Meta:
        unique_together = ('url', 'user')



class ShortProductLinkManager(models.Manager):
    def get_for_short_link(self, short_link):
        return ShortProductLink.objects.select_related('product').get(pk=(saturate(short_link) - SHORT_CONSTANT))


class ShortProductLink(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='short_product_links')
    created = models.DateTimeField(default=timezone.now)

    objects = ShortProductLinkManager()

    def link(self):
        return dehydrate(self.pk + SHORT_CONSTANT)

    class Meta:
        unique_together = ('product', 'user')


#
# VendorCategory
#

class VendorCategory(models.Model):
    category = TreeForeignKey(Category, verbose_name=_('category'), blank=True, null=True)
    name     = models.CharField(_('Name'), max_length=555)
    vendor   = models.ForeignKey(Vendor)
    default_gender = models.CharField(_('Default gender'), max_length=1, choices=PRODUCT_GENDERS, null=True, blank=True)
    override_gender = models.CharField(_('Override gender'), max_length=1, choices=PRODUCT_GENDERS, null=True, blank=True)
    modified = models.DateTimeField(_("Time modified"), auto_now=True, null=True, blank=True)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)

    # Update all related products to point to the category
    def save(self, *args, **kwargs):
        if self.category:
            queryset = Product.objects.filter(vendorproduct__vendor_category=self)
            for product in queryset:
                product.category = self.category
                product.save()

        if self.default_gender:
            queryset = Product.objects.filter(vendorproduct__vendor_category=self, gender__isnull=True)
            for product in queryset:
                product.gender = self.default_gender
                product.save()

        if self.override_gender:
            queryset = Product.objects.filter(vendorproduct__vendor_category=self)
            for product in queryset:
                product.gender = self.override_gender
                product.save()

            # NOTE 1: If we need to pre_save/post_save hooks for this, we need to explicitly call save()
            # NOTE 2: If we do not want to explicitly publish all related products (perhaps they are
            #   unpublished for a different reason?) we may want to do one of two things:
            #   1) Run code for each product to assess whether it should remain unpublished or not (see NOTE 1)
            #   2) Run a separate update query for all affected products who's category is None and set published=True

        # FIXME: Manually release cache for these objects
        super(VendorCategory, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'%s: %s <-> %s' % (self.vendor, self.name, self.category)

    class Meta:
        ordering = ['name']
        #unique_together = (('vendor', 'name'),)
        verbose_name_plural = 'vendor categories'


#
# VendorBrand
#

class VendorBrand(models.Model):
    """
    Vendor brand contains the brand name for vendor products.
    """
    name = models.CharField(max_length=100)
    brand = models.ForeignKey(Brand, related_name='vendor_brands', blank=True, null=True)
    vendor = models.ForeignKey(Vendor, related_name='vendor_brands')
    modified = models.DateTimeField(_("Time modified"), auto_now=True, null=True, blank=True)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.brand:
            for product in Product.objects.filter(vendorproduct__vendor_brand=self).iterator():
                if product.manufacturer_id != self.brand_id:
                    product.manufacturer_id = self.brand_id
                    product.save()
        else:
            queryset = Product.objects.filter(vendorproduct__vendor_brand=self, manufacturer__isnull=False)
            for product in queryset:
                product.manufacturer = None
                product.save()

        super(VendorBrand, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%s" % self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Vendor brand'
        verbose_name_plural = 'Vendor brands'


#
# VendorProduct
#

class VendorProduct(models.Model):
    product           = models.ForeignKey(Product, related_name='vendorproduct')
    vendor            = models.ForeignKey(Vendor)
    vendor_brand      = models.ForeignKey(VendorBrand, related_name='vendor_products', null=True)
    vendor_category   = models.ForeignKey(VendorCategory, related_name='vendor_products', null=True)
    buy_url           = models.URLField(_('Buy URL'), null=True, blank=True, max_length=555,)
    price             = models.DecimalField(_('Price'), null=True, blank=True, max_digits=10, decimal_places=2, db_index=True, help_text=_('Price converted to base currency'))
    currency          = models.CharField(_('Currency'), null=True, blank=True, max_length=3, help_text=_('Base currency as three-letter ISO code'))
    _original_price    = models.DecimalField(_('Original price'), db_column='original_price', null=True, blank=True, max_digits=10, decimal_places=2,)
    original_currency = models.CharField(_('Original currency'), null=True, blank=True, max_length=3, help_text=_('Currency as three-letter ISO code'))
    discount_price    = models.DecimalField(_('Discount price'), null=True, blank=True, max_digits=10, decimal_places=2)
    discount_currency = models.CharField(_('Discount currency'), null=True, blank=True, max_length=3, help_text=_('Currency as three-letter ISO code'))
    _original_discount_price = models.DecimalField(_('Original discount price'), db_column='original_discount_price', null=True, blank=True, max_digits=10, decimal_places=2)
    original_discount_currency = models.CharField(_('Original discount currency'), null=True, blank=True, max_length=3, help_text=_('Currency as three-letter ISO code'))
    availability  = models.IntegerField(_('Items in stock'), null=True, blank=True, help_text=_('Negative value means it is in stock, but we have no information about how many. Null means we have no information about availability. 0 means it is sold out'))

    @property
    def original_price(self):
        return self._original_price

    @original_price.setter
    def original_price(self, new_price):
        self.previous_original_price = self._original_price
        self._original_price = new_price

    @property
    def original_discount_price(self):
        return self._original_discount_price

    @original_discount_price.setter
    def original_discount_price(self, new_price):
        self.previous_original_discount_price = self._original_discount_price
        self._original_discount_price = new_price

    def _calculate_exchange_price(self):
        """
        Return price and currency based on the selected currency. If no
        currency is selected currency language is converted to a currency if
        possible else APPAREL_BASE_CURRENCY is used.
        """
        if not hasattr(self, '_calculated_locale_price'):
            to_currency = settings.LANGUAGE_TO_CURRENCY.get(get_language(), settings.APPAREL_BASE_CURRENCY)
            rate = currency_exchange(to_currency, self.original_currency)

            discount_price = self.original_discount_price
            if discount_price:
                discount_price = rate * self.original_discount_price

            self._calculated_locale_price = (rate * self.original_price, discount_price, to_currency)

        return self._calculated_locale_price

    @cached_property
    def locale_price(self):
        price, _, _ = self._calculate_exchange_price()
        return price

    @cached_property
    def locale_discount_price(self):
        _, discount_price, _ = self._calculate_exchange_price()
        return discount_price

    @cached_property
    def locale_currency(self):
        _, _, currency = self._calculate_exchange_price()
        return currency

    @cached_property
    def lowest_price_in_sek(self):
        rate = currency_exchange('SEK', self.original_currency)
        discount_price = self.original_discount_price
        if discount_price:
            return rate * self.original_discount_price

        return rate * self.original_price

    def __unicode__(self):
        return u'%s (%s)' % (self.product, self.vendor)

    class Meta:
        ordering = ['vendor', 'product']

    class Exporter:
        export_fields = ['__all__', '-product']

models.signals.post_save.connect(invalidate_model_handler, sender=VendorProduct)
models.signals.post_delete.connect(invalidate_model_handler, sender=VendorProduct)


@receiver(pre_save, sender=VendorProduct, dispatch_uid='vendor_product_pre_save')
def vendor_product_pre_save(sender, instance, **kwargs):

    if hasattr(instance, 'previous_original_discount_price') and instance.original_discount_price and instance.original_discount_price > decimal.Decimal('0.0'):
        price = discount_price = None

        # First discount observed
        if instance.previous_original_discount_price is None and instance.original_price is not None:
            price = decimal.Decimal(instance.original_price)
            discount_price = decimal.Decimal(instance.original_discount_price)
            first = True

        # Another discount observered if the change is larger than 10% of the
        # previous value
        elif instance.previous_original_discount_price > decimal.Decimal('0.0') and instance.previous_original_discount_price > decimal.Decimal('1.1') * decimal.Decimal(instance.original_discount_price):
            price = decimal.Decimal(instance.previous_original_discount_price)
            discount_price = decimal.Decimal(instance.original_discount_price)
            first = False

        # Only process sale alerts if price and discount price is set and the
        # vendorproduct has a product. The product should be available,
        # published and an manufacturer should be attached with a profile.
        if price and discount_price and instance.product and instance.product.manufacturer and instance.product.manufacturer.user and instance.product.availability == True and instance.product.published == True:
            process_sale_alert.delay(instance.product.manufacturer.user,
                                     instance.product,
                                     instance.original_currency,
                                     price,
                                     discount_price,
                                     first)


#
# VendorProductVariation
#

class VendorProductVariation(models.Model):
    """
    This class represents product combinations sold at a particular vendor
    """
    vendor_product = models.ForeignKey(VendorProduct, related_name='variations')
    # Negative value means it is in stock, but we have no information about how many
    # Null means we have no information about availability
    # 0 means it is sold out
    in_stock = models.IntegerField(_('Items in stock'), null=True, blank=True, help_text=_('Negative value means it is in stock, but we have no information about how many. Null means we have no information about availability. 0 means it is sold out'))
    options = models.ManyToManyField(Option)

    def __unicode__(self):
        if self.in_stock is None:
            s = _('No information available')
        elif self.in_stock == 0:
            s = _('Out of stock')
        elif self.in_stock < 0:
            s = _('In stock')
        else:
            s = '%i %s' % (self.in_stock, _('items in stock'))

        return unicode(s)

models.signals.post_save.connect(invalidate_model_handler, sender=VendorProductVariation)
models.signals.post_delete.connect(invalidate_model_handler, sender=VendorProductVariation)


#
# Look
#

def look_image_path(instance, filename):
    return os.path.join(settings.APPAREL_LOOK_IMAGE_ROOT, uuid.uuid4().hex)

def static_image_path(instance, filename):
    return os.path.join(settings.APPAREL_LOOK_IMAGE_ROOT, filename)

def validate_not_spaces(value):
    if value.strip() == '':
        raise ValidationError(u'You must provide more than just whitespace.')

class Look(models.Model):
    title = models.CharField(_('Title'), max_length=200, validators=[validate_not_spaces])
    slug  = AutoSlugField(_('Slug Name'), populate_from=("title",), blank=True,
                help_text=_('Used for URLs, auto-generated from name if blank'), max_length=80)
    description = models.TextField(_('Look description'), null=True, blank=True)
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='look')
    image       = ImageField(upload_to=look_image_path, max_length=255, blank=True)
    static_image = ImageField(upload_to=static_image_path, max_length=255, null=True, blank=True)
    created     = models.DateTimeField(_("Time created"), auto_now_add=True)
    modified    = models.DateTimeField(_("Time modified"), auto_now=True)
    tags        = TagField(blank=True)
    component   = models.CharField(_('What compontent to show'), max_length=1, choices=LOOK_COMPONENT_TYPES, blank=True)
    gender      = models.CharField(_('Gender'), max_length=1, choices=PRODUCT_GENDERS, null=False, blank=False, default='U')
    popularity  = models.DecimalField(default=0, max_digits=20, decimal_places=8, db_index=True)
    width       = models.IntegerField(blank=False, null=False, default=settings.APPAREL_LOOK_SIZE[0] - 2)
    height      = models.IntegerField(blank=False, null=False, default=settings.APPAREL_LOOK_SIZE[1] - 2)
    published   = models.BooleanField(default=False)

    image_width = models.IntegerField(blank=False, null=False, default=settings.APPAREL_LOOK_SIZE[0] - 2)
    image_height = models.IntegerField(blank=False, null=False, default=settings.APPAREL_LOOK_SIZE[1] - 2)

    objects = models.Manager()
    published_objects = LookManager()

    def save(self, *args, **kwargs):
        logger.debug('save slug %s, look_id %s, published: %s, gender: %s' % (self.slug, self.pk, self.published, self.gender))
        super(Look, self).save(*args, **kwargs)

    @staticmethod
    def build_static_image(look_id):
        """
        Build a static image of the look. Used for thumbnails and mails.
        """
        look = Look.objects.get(pk=look_id)

        # Build temporary static look image
        look.static_image = 'static/images/white.png'
        look.save(update_fields=['static_image', 'modified'])

        # Build static look image in background
        build_static_look_image.delay(look.pk)

    @staticmethod
    def calculate_gender(look_id, update=True):
        """
        Calculate looks gender based on displayed products.

        If ratio of either male or female products is larger than 0.5 select
        gender, else it is unisex.
        """
        look = Look.objects.get(pk=look_id)

        logger.debug('slug %s, look_id %s, published: %s' % (look.slug, look_id, look.published))

        genders = list(look.display_components.values_list('product__gender', flat=True))
        genders_len = float(len(genders))


        logger.debug('genders %s and length %s' % (genders, genders_len))

        user_gender = look.user.gender
        gender = user_gender if user_gender else 'U'
        if genders_len:
            if (genders.count('M') / genders_len) > 0.5:
                gender = 'M'
            elif (genders.count('W') / genders_len) > 0.5:
                gender = 'W'

        if update:
            logger.debug('update gender to %s' % (gender,))
            look.gender = gender
            look.save(update_fields=['gender', 'modified'])

        return gender

    @cached_property
    def score(self):
        return self.likes.filter(active=True).count()

    @cached_property
    def contest_score(self):
        return self.likes.filter(active=True, created__lte=datetime.datetime(2013, 9, 1, 23, 59, 59)).count()

    @cached_property
    def contest_xmas_menlook_score(self):
        return self.likes.filter(active=True, created__lte=datetime.datetime(2013, 12, 8, 23, 59, 59)).count()

    @cached_property
    def contest_jc_score(self):
        return self.likes.filter(active=True, created__lte=datetime.datetime(2014, 8, 30, 23, 59, 59)).count()

    @cached_property
    def comment_count(self):
        return Comment.objects.for_model(self).filter(is_removed=False, is_public=True).count()

    @cached_property
    def total_price(self):
        """
        Returns the total price of the given component, or default if none specified
        To get the price of all components, specify A
        """
        total = decimal.Decimal('0.0')
        for component in self.display_components:
            if component.product.default_vendor:
                if component.product.default_vendor.locale_discount_price:
                    total += component.product.default_vendor.locale_discount_price
                else:
                    total += component.product.default_vendor.locale_price

        return total

    @cached_property
    def photo_components(self):
        """
        All components in the photo view
        """
        return self.components.filter(component_of='P')

    @cached_property
    def collage_components(self):
        """
        All components in the collage view
        """
        return self.components.filter(component_of='C')

    @cached_property
    def display_components(self):
        """
        All components in the view that should be displayed according to the
        logic in "display_with_component"
        """
        return self.photo_components if self.display_with_component == 'P' else self.collage_components

    @cached_property
    def display_with_component(self):
        """
        Returns the component that should be displayed by default by
         1) Using the value of "component"
         2) Checking if there are more than 1 photo component, if so display as photo
         3) Collage
        """
        if self.component: return self.component
        if self.photo_components.count() > 0: return 'P'
        return 'C'

    @cached_property
    def is_collage(self):
        if self.component == 'C':
            return True

        return False

    @cached_property
    def product_manufacturers(self):
        return [x for x in self.display_components.values_list('product__manufacturer__name', flat=True) if x]

    @cached_property
    def product_brands_unique(self):
        return set(self.product_manufacturers)

    @cached_property
    def category_and_brand_with_product(self):
        return list(get_brand_and_category(self))

    def category_and_brand(self):
        return [x[0] for x in self.category_and_brand_with_product]

    def category_and_brand_count(self):
        return len(self.category_and_brand_with_product)

    def __unicode__(self):
        return u"%s by %s" % (self.title, self.user.display_name)

    @models.permalink
    def get_absolute_url(self):
        return ('look-detail', [str(self.slug)])

    class Meta:
        ordering = ['user', 'title']

    class Exporter:
        export_fields = ['__all__', 'get_absolute_url', 'photo_components', 'display_with_component', 'collage_components', 'score']

models.signals.post_save.connect(invalidate_model_handler, sender=Look)
models.signals.post_delete.connect(invalidate_model_handler, sender=Look)

@receiver(look_saved, sender=Look, dispatch_uid='look_saved')
def look_saved_handler(sender, look, **kwargs):
    if not hasattr(look, 'user'):
        logging.warning('Trying to register an activity on post_save, but %s has not user attribute' % look)
        return

    # Calculate gender and add it to the current look object
    look.gender = get_model('apparel', 'Look').calculate_gender(look.pk)

    if kwargs.get('update', True):
        # Build static image
        get_model('apparel', 'Look').build_static_image(look.pk)
        empty_embed_look_cache.apply_async(args=[look.slug], countdown=1)

    if look.published == True:
        get_model('activity_feed', 'activity').objects.push_activity(look.user, 'create', look, look.gender)
    else:
        get_model('activity_feed', 'activity').objects.pull_activity(look.user, 'create', look)

@receiver(pre_delete, sender=Look, dispatch_uid='look_pre_delete')
def look_pre_delete(sender, instance, **kwargs):
    if not hasattr(instance, 'user'):
        logging.warning('Trying to remove an activity on pre_delete, but %s has not user attribute' % instance)
        return

    get_model('activity_feed', 'activity').objects.pull_activity(instance.user, 'create', instance)

#
# LookEmbed
#

class LookEmbed(models.Model):
    """
    Store a unique embed id for looks.
    """
    identifier = models.CharField(max_length=32, null=False, blank=False, unique=True)
    look = models.ForeignKey(Look, related_name='embeds', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='look_embeds')
    language = models.CharField(max_length=3, null=False, blank=False)
    width = models.IntegerField(null=False, blank=False)
    width_type = models.CharField(max_length=2, null=False, blank=False, default='px')
    created = models.DateTimeField(_("Time created"), auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['-created']

#
# LookLike
#

class LookLike(models.Model):
    """
    Keep track of likes on looks
    """
    look = models.ForeignKey(Look, related_name='likes', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='look_likes')
    created = models.DateTimeField(_("Time created"), auto_now_add=True, null=True, blank=True)
    modified = models.DateTimeField(_("Time modified"), auto_now=True, null=True, blank=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return u'%s likes look %s' % (self.user, self.look)

    class Meta:
        unique_together = (('look', 'user'),)

models.signals.post_save.connect(invalidate_model_handler, sender=LookLike)
models.signals.post_delete.connect(invalidate_model_handler, sender=LookLike)

@receiver(post_save, sender=LookLike, dispatch_uid='look_like_post_save')
def look_like_post_save(sender, instance, **kwargs):
    if not hasattr(instance, 'user'):
        logging.warning('Trying to register an activity, but %s has not user attribute' % instance)
        return

    if instance.active == True and instance.look.published == True:
        get_model('activity_feed', 'activity').objects.push_activity(instance.user, 'like_look', instance.look, instance.look.gender)
    else:
        get_model('activity_feed', 'activity').objects.pull_activity(instance.user, 'like_look', instance.look)

@receiver(pre_delete, sender=LookLike, dispatch_uid='look_like_pre_delete')
def look_like_pre_delete(sender, instance, **kwargs):
    if not hasattr(instance, 'user'):
        logging.warning('Trying to remove an activity, but %s has not user attribute' % instance)
        return

    get_model('activity_feed', 'activity').objects.pull_activity(instance.user, 'like_look', instance.look)


#
# LookComponent
#

class LookComponent(models.Model):
    """
    This class maps a product to a collage or uploaded image of a look and
    contains necessary information to display the product's image there in.
    """
    look    = models.ForeignKey(Look, related_name='components')
    product = models.ForeignKey(Product)
    component_of = models.CharField(max_length=1, choices=LOOK_COMPONENT_TYPES)
    top = models.IntegerField(_('CSS top'), blank=True, null=True)
    left = models.IntegerField(_('CSS left'), blank=True, null=True)
    width = models.IntegerField(_('CSS width'), blank=True, null=True)
    height = models.IntegerField(_('CSS height'), blank=True, null=True)
    z_index = models.IntegerField(_('CSS z-index'), blank=True, null=True)
    rotation = models.IntegerField(_('CSS rotation'), blank=True, null=True)
    positioned = models.CharField(max_length=1, choices=LOOK_COMPONENT_POSITIONED, null=True, blank=True)

    # FIXME: Scale product image on initial save and store height and width
    # properties

    def _style(self, scale=1, percentage=False):
        s = []

        if self.component_of == 'P':
            attrs = {}
            for attr in ('top', 'left', 'width', 'height'):
                if(attr in self.__dict__.keys() and self.__dict__[attr] is not None):
                    attrs[attr] = self.__dict__[attr] * scale

            s.append('width: %spx;' % (self.width,))
            s.append('height: %spx;' % (self.height,))
            s.append('top: %spx;' % (attrs['top'] + (attrs['height'] - self.height) / 2,))
            s.append('left: %spx;' % (attrs['left'] + (attrs['width'] - self.width) / 2,))
        else:
            for attr in ('top', 'left', 'width', 'height'):
                if(attr in self.__dict__.keys() and self.__dict__[attr] is not None):
                    s.append("%s: %spx;" % (attr, self.__dict__[attr] * scale),)

        if self.z_index:
            s.append('z-index: %s;' % (self.z_index,))

        if self.rotation:
            s.append('transform: rotate(%sdeg); ' % self.rotation)
            s.append('-moz-transform: rotate(%sdeg); ' % self.rotation)
            s.append('-webkit-transform: rotate(%sdeg); ' % self.rotation)
            s.append('-o-transform: rotate%sdeg); ' % self.rotation)
            s.append('-ms-transform: rotate(%sdeg); ' % self.rotation)

        return " ".join(s)

    def _calculate_width(self, fixed_width, fixed_height):
        width = float(self.look.width)
        height = float(self.look.height)

        factor = min(fixed_width / width, fixed_height / height)
        if factor < 1:
            width = round(width * factor, 0)

        return width

    @property
    def style_small(self):
        return self._style(self._calculate_width(93, 69) / float(self.look.width))

    @property
    def style_middle(self):
        return self._style(self._calculate_width(450, 334) / float(self.look.width))

    @property
    def style_search(self):
        return self._style(self._calculate_width(200, 149) / float(self.look.width))

    def style_percentage(self, width=None, height=None):
        s = []
        if self.component_of == 'P':
            if width is None:
                width = self.width

            if height is None:
                height = self.height

            s.append('width: %spx;' % (80,))
            s.append('height: %spx;' % (80,))
            s.append('top: %s%%;' % ((self.top + self.height / 2) / float(self.look.height) * 100,))
            s.append('left: %s%%;' % ((self.left + self.width/2) / float(self.look.width) * 100,))

        else:
            s.append('width: %s%%;' % (self.width / float(self.look.width) * 100,))
            s.append('height: %s%%;' % (self.height / float(self.look.height) * 100,))
            s.append('top: %s%%;' % (self.top / float(self.look.height) * 100,))
            s.append('left: %s%%;' % (self.left / float(self.look.width) * 100,))

        if self.z_index:
            s.append('z-index: %s;' % (self.z_index,))

        if self.rotation:
            s.append('transform: rotate(%sdeg); ' % self.rotation)
            s.append('-moz-transform: rotate(%sdeg); ' % self.rotation)
            s.append('-webkit-transform: rotate(%sdeg); ' % self.rotation)
            s.append('-o-transform: rotate%sdeg); ' % self.rotation)
            s.append('-ms-transform: rotate(%sdeg); ' % self.rotation)

        return ' '.join(s)

    @property
    def style(self):
        return self._style(1)

    def save(self, *args, **kwargs):
        if self.component_of == 'C' and self.product.product_image and not self.height and not self.width:
            # This scales collage images to maximum size if height and width isn't defined
            thumb = get_thumbnail(self.product.product_image, '%sx%s' % (settings.APPAREL_LOOK_MAX_SIZE, settings.APPAREL_LOOK_MAX_SIZE), crop='noop', quality=99)
            self.width = thumb.width
            self.height = thumb.height

        super(LookComponent, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%s (%s, %s [%sx%s] %s) in %s" % (self.product, self.top, self.left, self.width, self.height, self.z_index, self.look)

    class Exporter:
        export_fields = ['__all__', 'style', 'style_middle', 'style_small', '-look']

models.signals.post_save.connect(invalidate_model_handler, sender=LookComponent)
models.signals.post_delete.connect(invalidate_model_handler, sender=LookComponent)


#
# InternalReferral
#

class InternalReferral(models.Model):
    cookie_id = models.CharField(max_length=32, null=False, blank=False, db_index=True)
    old_cookie_id = models.CharField(max_length=32, null=True, blank=True)

    sid = models.CharField(max_length=32, null=False, blank=False)
    page = models.CharField(max_length=32, null=False, blank=False)
    user_id = models.CharField(max_length=32, null=True, blank=True)
    expired = models.BooleanField(default=False)

    created = models.DateTimeField(null=False, blank=False)
    expires = models.DateTimeField(null=False, blank=False)

    class Meta:
        ordering = ['-created']

    def __unicode__(self):
        return u'InternalReferral(%s)' % (self.cookie_id,)


#
# TemporaryImage
#

class TemporaryImage(models.Model):
    image = models.ImageField(upload_to=settings.APPAREL_TEMPORARY_IMAGE_ROOT, max_length=255, null=False, blank=False)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)
    user_id = models.IntegerField(default=0)

    def __unicode__(self):
        return u'%s (uid=%s)' % (self.image, self.user_id)

#
# BackgroundImage
#

class BackgroundImageManager(models.Manager):
    def get_random_image(self):
        try:
            return self.order_by('?')[0].image
        except IndexError:
            pass

        return ''

class BackgroundImage(models.Model):
    image = models.ImageField(_('Image'), upload_to=settings.APPAREL_BACKGROUND_IMAGE_ROOT, max_length=255, null=True, blank=True)

    objects = BackgroundImageManager()

    def __unicode__(self):
        return u'%s' % (self.image,)


#
# ProductUsedWeekly
#

class ProductUsedWeekly(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=False, blank=False)


#
# FacebookAction
#

class FacebookAction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='facebook_actions')
    action = models.CharField(max_length=30)
    action_id = models.CharField(max_length=30)
    object_type = models.CharField(max_length=30)
    object_url = models.CharField(max_length=255)

    def __unicode__(self):
        return u'%s: %s' % (self.action, self.action_id)

#
# SynonymFile
#

def save_synonym_file(sender, **kwargs):
    instance = kwargs['instance']
    synonym_file = open(settings.SOLR_SYNONYM_FILE, "w")
    synonym_file.write(instance.content.encode("utf-8"))
    synonym_file.close()

    requests.get(settings.SOLR_RELOAD_URL)

class SynonymFile(models.Model):
    content = models.TextField(_('Synonyms'), null=True, blank=True, help_text=_('Place all synonyms on their own line, comma-separated. Comments start with "#".'))

    def __unicode__(self):
        return u'%s...' % (self.content[0:20],)

    def clean(self):
        if not hasattr(settings, "SOLR_SYNONYM_FILE"):
            raise ValidationError("You must define the SOLR_SYNONYM_FILE setting before using synonyms.")

        if self.__class__.objects.count() > 1:
            raise ValidationError("Only one synonym file is allowed.")

        for line in self.content.split("\n"):
            line = line.strip()

            # Don't bother with empty lines or comments
            if line == "" or line.startswith("#"):
                continue

            if not ("," in line or "=>" in line):
                raise ValidationError('Lines must contain at least one comma (or "=>")')

            if line.startswith(",") or line.endswith(",") or line.startswith("=>") or line.endswith("=>"):
                raise ValidationError('Lines can not start or end with "," or "=>"')

models.signals.post_save.connect(save_synonym_file, sender=SynonymFile)


#
# Comments
#

import django.contrib.comments.signals
django.contrib.comments.signals.comment_was_posted.connect(invalidate_model_handler)


#
# Search
#

import apparelrow.apparel.search
