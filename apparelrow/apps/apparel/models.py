import logging
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import get_language, ugettext_lazy as _
from django.template.defaultfilters import slugify

from apps.apparel.manager import SearchManager

import datetime, mptt

# FIXME: Move to Django settings directory
PRODUCT_IMAGE_BASE = 'static/product'
LOGOTYPE_BASE      = 'static/logos'


class Manufacturer(models.Model):
    name   = models.CharField(max_length=50, unique=True)
    active = models.BooleanField(default=False, help_text=_("Products can only be displayed for an active manufactorer"))
    logotype = models.ImageField(upload_to=LOGOTYPE_BASE, help_text=_('Logotype')) 
    homepage = models.URLField(_('Home page'))

    objects = SearchManager()

    def __unicode__(self):
        return self.name

    class Exporter:
        export_fields = ['__all__', '-active']


class OptionType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("Option Type")
        verbose_name_plural = _("Option Types")

try:
    mptt.register(OptionType, order_insertion_by=['name'])
except mptt.AlreadyRegistered:
    logging.debug("Attempt to register option type, but it's already registered")

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



class Vendor(models.Model):
    name     = models.CharField(max_length=100)
    homepage = models.URLField(_('Home page'))
    logotype = models.ImageField(upload_to=LOGOTYPE_BASE, help_text=_('Logotype')) 

    objects = SearchManager()

    def __unicode__(self):
        return u"%s" % (self.name) 


class Category(models.Model):
    key    = models.CharField(max_length=100, unique=True, blank=True)
    name   = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')
    active = models.BooleanField(default=False, help_text=_('Only active categories are visible and searchable on the website'))
    option_types = models.ManyToManyField(OptionType, blank=True, verbose_name=_('Option types'))
    
    objects = SearchManager()

    def save(self, force_insert=False, force_update=False):
        if not self.key and self.name:
            self.key = self.key_for_name(self.name)
        
        # FIXME: Can you get Django to auto truncate fields?
        self.name = self.name[:100]
        super(Category, self).save(force_insert=force_insert, force_update=force_update)
    
    def __unicode__(self):
        return self.name
    
    
    @staticmethod
    def key_for_name(name):
        field = Category._meta.get_field_by_name('key')[0]
        key   = slugify(name)
        
        return key[:field.max_length]
    
    class Exporter:
        export_fields = ['name', 'option_types']

try:
    mptt.register(Category, order_insertion_by=['name'])
except mptt.AlreadyRegistered:
    logging.debug("Attempt to register category, but it's already registered")

class Product(models.Model):
    manufacturer = models.ForeignKey(Manufacturer)
    category = models.ManyToManyField(Category, blank=True, verbose_name=_("Category"))
    options  = models.ManyToManyField(Option,   blank=True, verbose_name=_("Option"))
    slug = models.SlugField(_("Slug Name"), blank=True,
        help_text=_("Used for URLs, auto-generated from name if blank"), max_length=80)
    sku = models.CharField(_("Stock Keeping Unit"), max_length=255, blank=False, null=False,
        help_text=_("Has to be unique with the manufacturer"))
    product_name  = models.CharField(max_length=200)
    date_added    = models.DateTimeField(_("Time added"), null=True, blank=True)
    description   = models.TextField(_('Product description'), null=True, blank=True)
    product_image = models.ImageField(upload_to=PRODUCT_IMAGE_BASE, help_text=_('Product image')) 
    
    objects = SearchManager()
    
    def __unicode__(self):
        return u"%s %s" % (self.manufacturer, self.product_name)

    def save(self, force_insert=False, force_update=False):
        if not self.pk:
            self.date_added = datetime.date.today()

        if self.product_name and not self.slug:
            self.slug = slugify(self.manufacturer.name + " " + self.product_name)

        if not self.sku:
            self.sku = self.slug

        super(Product, self).save(force_insert=force_insert, force_update=force_update)
    
    class Exporter:
        export_fields = ['__all__', 'vendorproduct']

class VendorProduct(models.Model):
    vendor     = models.ForeignKey(Vendor)
    product    = models.ForeignKey(Product, related_name='vendorproduct')
    buy_url    = models.URLField(_('Buy URL'), null=True, blank=True, )
    price      = models.DecimalField(_('Numeric price'), null=True, blank=True, max_digits=10, decimal_places=2)
    currency   = models.CharField(_('Currency'), null=True, blank=True, max_length=3, help_text=_('Currency as three-letter ISO code'))
    
    def __unicode__(self):
        return u'%s (%s)' % (self.product, self.vendor)



class Look(models.Model):
    title = models.CharField(max_length=200)
    products = models.ManyToManyField(Product, through='LookProduct')
    user = models.ForeignKey(User)
    image = models.ImageField(upload_to='looks')

    def __unicode__(self):
        return u"%s by %s" % (self.title, self.user)

    @models.permalink
    def get_absolute_url(self):
        return ('apps.apparel.views.look_detail', [str(self.id)])

class LookProduct(models.Model):
    product = models.ForeignKey(Product)
    look = models.ForeignKey(Look, related_name='look_products')
    top = models.IntegerField(_('CSS top'), blank=True, null=True)
    left = models.IntegerField(_('CSS left'), blank=True, null=True)
    width = models.IntegerField(_('CSS width'), blank=True, null=True)
    height = models.IntegerField(_('CSS height'), blank=True, null=True)
    z_index = models.IntegerField(_('CSS z-index'), blank=True, null=True)

    def __unicode__(self):
        return u"%s (%s, %s [%sx%s] %s) in %s" % (self.product, self.top, self.left, self.width, self.height, self.z_index, self.look)

    class Meta:
        unique_together     = (('product', 'look'),)
