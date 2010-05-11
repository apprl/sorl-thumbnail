import logging
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import get_language, ugettext_lazy as _
from django.template.defaultfilters import slugify
from django.conf import settings

from apparel.manager import SearchManager

import datetime, mptt
import tagging
from tagging.fields import TagField
from sorl.thumbnail.main import DjangoThumbnail

from django_extensions.db.fields import AutoSlugField

# FIXME: Move to Django settings directory
LOGOTYPE_BASE      = 'static/logos'
LOOKS_BASE         = 'static/looks'

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
    key           = models.CharField(max_length=100, unique=True, blank=True)
    name          = models.CharField(max_length=100)
    parent        = models.ForeignKey('self', null=True, blank=True, related_name='children')
    active        = models.BooleanField(default=False, help_text=_('Only active categories are visible and searchable on the website'))
    option_types  = models.ManyToManyField(OptionType, blank=True, verbose_name=_('Option types'))
    on_front_page = models.BooleanField(default=False, help_text=_('The category is visible on the front page'))

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
    
    class Meta:
        verbose_name_plural = 'categories'

try:
    mptt.register(Category, order_insertion_by=['name'])
except mptt.AlreadyRegistered:
    logging.debug("Attempt to register category, but it's already registered")


class CategoryAlias(models.Model):
    category = models.ForeignKey(Category)
    alias    = models.CharField(_('Alias'), max_length=255, unique=True, blank=True)
    
    def __unicode__(self):
        return '%s alias to %s' % (self.alias, self.category.name)

class Product(models.Model):
    manufacturer = models.ForeignKey(Manufacturer)
    category = models.ForeignKey(Category)
    options  = models.ManyToManyField(Option, blank=True, verbose_name=_("Option"))
    slug = AutoSlugField(_("Slug Name"), populate_from=("manufacturer", "product_name",), blank=True,
        help_text=_("Used for URLs, auto-generated from name if blank"), max_length=80)
    sku = models.CharField(_("Stock Keeping Unit"), max_length=255, blank=False, null=False,
        help_text=_("Has to be unique with the manufacturer"))
    product_name  = models.CharField(max_length=200)
    date_added    = models.DateTimeField(_("Time added"), null=True, blank=True)
    description   = models.TextField(_('Product description'), null=True, blank=True)
    product_image = models.ImageField(upload_to=settings.APPAREL_PRODUCT_IMAGE_ROOT, help_text=_('Product image')) 
    
    objects = SearchManager()
    
    @property
    def default_vendor(self):
        return self.vendorproduct.order_by('price')[0]

    @models.permalink
    def get_absolute_url(self):
        return ('apparel.views.product_detail', [str(self.slug)])

    def save(self, force_insert=False, force_update=False):
        if not self.pk:
            self.date_added = datetime.date.today()

        if not self.sku:
            self.sku = self.slug

        super(Product, self).save(force_insert=force_insert, force_update=force_update)

    def __unicode__(self):
        return u"%s %s" % (self.manufacturer, self.product_name)
    
    class Meta:
        ordering = ('-date_added',)
    
    class Exporter:
        export_fields = ['__all__', 'get_absolute_url', 'default_vendor']

class VendorProduct(models.Model):
    vendor     = models.ForeignKey(Vendor)
    product    = models.ForeignKey(Product, related_name='vendorproduct')
    buy_url    = models.URLField(_('Buy URL'), null=True, blank=True, )
    price      = models.DecimalField(_('Numeric price'), null=True, blank=True, max_digits=10, decimal_places=2)
    currency   = models.CharField(_('Currency'), null=True, blank=True, max_length=3, help_text=_('Currency as three-letter ISO code'))
    
    def __unicode__(self):
        return u'%s (%s)' % (self.product, self.vendor)

    class Exporter:
        export_fields = ['__all__', '-product']


class Look(models.Model):
    title = models.CharField(_('Title'), max_length=200)
    slug  = AutoSlugField(_('Slug Name'), populate_from=("title",), blank=True,
                help_text=_('Used for URLs, auto-generated from name if blank'), max_length=80)
    description = models.TextField(_('Look description'), null=True, blank=True)
    products    = models.ManyToManyField(Product)
    user        = models.ForeignKey(User)
    image       = models.ImageField(upload_to=LOOKS_BASE, blank=True)
    created     = models.DateTimeField(_("Time created"), auto_now_add=True)
    modified    = models.DateTimeField(_("Time modified"), auto_now=True)
    tags        = TagField()
    
    @property
    def total_price(self):
        prices = [p.default_vendor.price for p in self.products.all()]
        return sum(prices)

    def __unicode__(self):
        return u"%s by %s" % (self.title, self.user)

    @models.permalink
    def get_absolute_url(self):
        return ('apparel.views.look_detail', [str(self.slug)])
    
    class Exporter:
        export_fields = ['__all__']

class LookComponent(models.Model):
    """
    This class maps a product to a collage or uploaded image of a look and 
    contains necessary information to display the product's image there in.
    """
    look    = models.ForeignKey(Look, related_name='components')
    product = models.ForeignKey(Product)
    component_of = models.CharField(max_length=1, choices=(
        ('C', 'Collage'),
        ('P', 'Picture'),
    ))
    top = models.IntegerField(_('CSS top'), blank=True, null=True)
    left = models.IntegerField(_('CSS left'), blank=True, null=True)
    width = models.IntegerField(_('CSS width'), blank=True, null=True)
    height = models.IntegerField(_('CSS height'), blank=True, null=True)
    z_index = models.IntegerField(_('CSS z-index'), blank=True, null=True)
    rotation = models.IntegerField(_('CSS rotation'), blank=True, null=True)
    # FIXME: Scale product image on initial save and store height and width
    # properties 

    def _style(self, scale=1):
        s = []
        for attr in ('top', 'left', 'width', 'height', 'z_index'):
            if(attr in self.__dict__.keys() and self.__dict__[attr]):
                s.append("%s: %spx;" % (attr.replace('_', '-'), self.__dict__[attr] * scale))
        
        if self.rotation:
            s.append('-moz-transform: rotate(%sdeg); ' % self.rotation)
            s.append('-webkit-transform: rotate(%sdeg); ' % self.rotation)
            
        return " ".join(s)
    
    @property
    def style_small(self):
        return self._style(1.0 / 7.0)

    @property
    def style_middle(self):
        return self._style(0.65)

    @property
    def style(self):
        return self._style(1)
    
    def save(self, *args, **kwargs):
        if self.product.product_image and not self.height and not self.width:
            # FIXME: Does this only scale the image  if it isn't already scaled? 
            # Performance-wise, it probably should and just give us the dimensions
            thumb = DjangoThumbnail(self.product.product_image, (
                                        settings.APPAREL_LOOK_MAX_SIZE, 
                                        settings.APPAREL_LOOK_MAX_SIZE
                                    ))
            self.width  = thumb.data.size[0]
            self.height = thumb.data.size[1]
        
        super(LookComponent, self).save(*args, **kwargs)
    
    def __unicode__(self):
        return u"%s (%s, %s [%sx%s] %s) in %s" % (self.product, self.top, self.left, self.width, self.height, self.z_index, self.look)

    class Meta:
        unique_together = (('product', 'look', 'component_of'),)

    class Exporter:
        export_fields = ['__all__', 'style']



class Wardrobe(models.Model):
    user     = models.ForeignKey(User)
    products = models.ManyToManyField(Product)
    
    def __unicode__(self):
        return 'Wardrobe for %s' % self.user
