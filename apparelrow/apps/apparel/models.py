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


class OptionType(models.Model):
    TYPE_GROUP_CHOICES = (
        (None,   'Nothing'),
        ('size', 'Size'),
    )

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=100)
    type_group = models.CharField(_('Type group'), max_length=10, null=True, 
        blank=True, choices=TYPE_GROUP_CHOICES)
    
    class Meta:
        ordering = ['name']
        verbose_name = _("Option Type")
        verbose_name_plural = _("Option Types")
    
    def __unicode__(self):
        return self.name



class Option(models.Model):
    value       = models.CharField(_('Option value'), max_length=255)
    option_type = models.ForeignKey(OptionType)

    class Meta:
        ordering = ['option_type']
        unique_together     = (('option_type', 'value'),)
        verbose_name        = _('Option Item')
        verbose_name_plural = _('Option Items')

    def __unicode__(self):
        return "%s: %s" % (self.option_type.name, self.value) 


class Vendor(models.Model):
    name     = models.CharField(max_length=100)
    homepage = models.URLField(_('Home page'))
    logotype = models.ImageField(upload_to=LOGOTYPE_BASE, help_text=_('Logotype')) 

    objects = SearchManager()

    def __unicode__(self):
        return "%s" % (self.name) 


class Category(models.Model):
    key    = models.CharField(max_length=100, unique=True, blank=True)
    name   = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')
    active = models.BooleanField(default=False, help_text=_('Only active categories are visible and searchable on the website'))
    option_types = models.ManyToManyField(OptionType, blank=True, verbose_name=_('Option types'))
    
    objects = SearchManager()

    def save(self, force_insert=False, force_update=False):
        if not self.key and self.name:
            self.key = slugify(self.name)
        
        super(Category, self).save(force_insert=force_insert, force_update=force_update)

    def __unicode__(self):
        return self.name

try:
    mptt.register(Category, order_insertion_by=['name'])
except mptt.AlreadyRegistered:
    # FIXME: Use a debug statement here
    print "Attempt to register category, but it's already registered"

class Product(models.Model):
    manufacturer = models.ForeignKey(Manufacturer)
    category = models.ManyToManyField(Category, blank=True, verbose_name=_("Category"))
    options  = models.ManyToManyField(Option,   blank=True, verbose_name=_("Option"))
    slug = models.SlugField(_("Slug Name"), blank=True,
        help_text=_("Used for URLs, auto-generated from name if blank"), max_length=80)
    sku = models.CharField(_("Stock Keeping Unit"), max_length=255, blank=False, null=False,
        help_text=_("Has to be unique with the manufacturer"))
    product_name  = models.CharField(max_length=200)
    date_added    = models.DateField(_("Date added"), null=True, blank=True)
    description   = models.TextField(_('Product description'), null=True, blank=True)
    product_image = models.ImageField(upload_to=PRODUCT_IMAGE_BASE, help_text=_('Product image')) 
    
    objects = SearchManager()
    
    def __unicode__(self):
        return "%s %s" % (self.manufacturer, self.product_name)

    def save(self, force_insert=False, force_update=False):
        if not self.pk:
            self.date_added = datetime.date.today()

        if self.product_name and not self.slug:
            self.slug = slugify(self.manufacturer.name + " " + self.product_name)

        if not self.sku:
            self.sku = self.slug

        super(Product, self).save(force_insert=force_insert, force_update=force_update)

    class Meta:
        pass


class VendorProduct(models.Model):
    vendor     = models.ForeignKey(Vendor)
    product    = models.ForeignKey(Product)
    buy_url    = models.URLField(_('Buy URL'), null=True, blank=True, )
    price      = models.DecimalField(_('Numeric price'), null=True, blank=True, max_digits=10, decimal_places=2)
    currency   = models.CharField(_('Currency'), null=True, blank=True, max_length=3, help_text=_('Currency as three-letter ISO code'))
    
    def __unicode__(self):
        return u'%s (%s)' % (self.product, self.vendor)



class Look(models.Model):
    title = models.CharField(max_length=200)
    products = models.ManyToManyField(Product)
    user = models.ForeignKey(User)
    image = models.ImageField(upload_to='looks')

    def __unicode__(self):
        return "%s by %s" % (self.title, self.user)

