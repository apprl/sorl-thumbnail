import logging
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import get_language, ugettext_lazy as _
from django.template.defaultfilters import slugify
from django.conf import settings
from django.db.models import Sum, Min

from apparel.manager import SearchManager, FeaturedManager, FirstPageManager
from apparel import cache

import datetime, mptt, tagging
from tagging.fields import TagField
from voting.models import Vote
from sorl.thumbnail.main import DjangoThumbnail

from django_extensions.db.fields import AutoSlugField

class Manufacturer(models.Model):
    name   = models.CharField(max_length=50, unique=True)
    active = models.BooleanField(default=False, help_text=_("Products can only be displayed for an active manufactorer"))
    logotype = models.ImageField(upload_to=settings.APPAREL_LOGO_IMAGE_ROOT, max_length=127, help_text=_('Logotype')) 
    homepage = models.URLField(_('Home page'))

    objects = SearchManager()

    def __unicode__(self):
        return u"%s" % self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("Manufacturer")

    class Exporter:
        export_fields = ['__all__', '-active']


class OptionType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

    def __unicode__(self):
        return u"%s" % self.name

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
    logotype = models.ImageField(upload_to=settings.APPAREL_LOGO_IMAGE_ROOT, help_text=_('Logotype'), max_length=127, blank=True, null=True) 

    objects = SearchManager()

    class Meta:
        ordering = ['name']
        verbose_name = _("Vendor")

    def __unicode__(self):
        return u"%s" % self.name


class Category(models.Model):
    name          = models.CharField(max_length=100)
    parent        = models.ForeignKey('self', null=True, blank=True, related_name='children')
    active        = models.BooleanField(default=False, help_text=_('Only active categories are visible and searchable on the website'))
    option_types  = models.ManyToManyField(OptionType, blank=True, verbose_name=_('Option types'))
    on_front_page = models.BooleanField(default=False, help_text=_('The category is visible on the front page'))
    
    def save(self, *args, **kwargs):
        # FIXME: Can you get Django to auto truncate fields?
        self.name = self.name[:100]
        super(Category, self).save(*args, **kwargs)
    
    def __unicode__(self):
        return u"%s" % self.name
    
    class Exporter:
        export_fields = ['name', 'option_types']
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'


try:
    mptt.register(Category, order_insertion_by=['name'])
except mptt.AlreadyRegistered:
    logging.debug("Attempt to register category, but it's already registered")

models.signals.post_save.connect(cache.invalidate_model_handler, sender=Category)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=Category)

PRODUCT_GENDERS = (
    ('W', 'Women',),
    ('M', 'Men',),
    ('U', 'Unisex',),
)

class Product(models.Model):
    manufacturer = models.ForeignKey(Manufacturer)
    category = models.ForeignKey(Category, blank=True, null=True)
    options  = models.ManyToManyField(Option,   blank=True, verbose_name=_("Option"))
    slug = AutoSlugField(_("Slug Name"), populate_from=("manufacturer", "product_name",), blank=True,
        help_text=_("Used for URLs, auto-generated from name if blank"), max_length=80)
    sku = models.CharField(_("Stock Keeping Unit"), max_length=255, blank=False, null=False,
        help_text=_("Has to be unique with the manufacturer"))
    product_name  = models.CharField(max_length=200, null=True, blank=True)
    date_added    = models.DateTimeField(_("Time added"), null=True, blank=True)
    description   = models.TextField(_('Product description'), null=True, blank=True)
    product_image = models.ImageField(upload_to=settings.APPAREL_PRODUCT_IMAGE_ROOT, max_length=255, help_text=_('Product image')) 
    vendors       = models.ManyToManyField(Vendor, through='VendorProduct')
    gender        = models.CharField(_('Gender'), max_length=1, choices=PRODUCT_GENDERS, null=True, blank=True)
    published     = models.BooleanField(default=True)
    
    objects = SearchManager()
    
    def score(self):
        return Vote.objects.get_score(self)
    
    @property
    def default_vendor(self):
        if self.vendorproduct.order_by('price').count() == 0: return None
        return self.vendorproduct.order_by('price')[0]

    @models.permalink
    def get_absolute_url(self):
        return ('apparel.views.product_detail', [str(self.slug)])
    
    def categories(self):
        c = self.category
        categories = []
                
        while c:
            categories.insert(0, c)
            c = c.parent
        
        return categories

    def save(self, *args, **kwargs):
        if not self.pk:
            self.date_added = datetime.date.today()

        if not self.sku:
            self.sku = self.slug
        
        if not self.category:
            self.published = False

        if not self.gender:
            try:
                self.gender = self.vendorproduct.get().vendor_category.default_gender
            except:
                pass

        super(Product, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%s %s" % (self.manufacturer, self.product_name)
    
    class Meta:
        ordering = ('-date_added',)
    
    class Exporter:
        export_fields = ['__all__', 'get_absolute_url', 'default_vendor', 'score']

models.signals.post_save.connect(cache.invalidate_model_handler, sender=Product)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=Product)


# Maps products for a specific vendor 
# This is used for importing stuff - when this category is changed,
# all related products will be updated to reflect the category
class VendorCategory(models.Model):
    category = models.ForeignKey(Category, verbose_name=_('category'), null=True)
    name     = models.CharField(_('Name'), max_length=255)
    vendor   = models.ForeignKey(Vendor)
    default_gender = models.CharField(_('Default gender'), max_length=1, choices=PRODUCT_GENDERS, null=True, blank=True)
    
    # Update all related products to point to the category
    def save(self, *args, **kwargs):
        if self.category:
            Product.objects.filter(vendorproduct__vendor_category=self).update(
                category=self.category,
                published=True
            )
        if self.default_gender:
            Product.objects.filter(vendorproduct__vendor_category=self, gender__isnull=True).update(
                gender=self.default_gender
            )
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
        unique_together = (('vendor', 'name'),)
        verbose_name_plural = 'vendor categories'


class VendorProduct(models.Model):
    vendor            = models.ForeignKey(Vendor)
    product           = models.ForeignKey(Product, related_name='vendorproduct')
    vendor_category   = models.ForeignKey(VendorCategory, related_name='vendorproducts', null=True,)
    buy_url           = models.URLField(_('Buy URL'), null=True, blank=True, max_length=255,)
    price             = models.DecimalField(_('Price'), null=True, blank=True, max_digits=10, decimal_places=2, db_index=True, help_text=_('Price converted to base currency'))
    currency          = models.CharField(_('Currency'), null=True, blank=True, max_length=3, help_text=_('Base currency as three-letter ISO code'))
    original_price    = models.DecimalField(_('Original price'), null=True, blank=True, max_digits=10, decimal_places=2,)
    original_currency = models.CharField(_('Original currency'), null=True, blank=True, max_length=3, help_text=_('Currency as three-letter ISO code'))
    
    def __unicode__(self):
        return u'%s (%s)' % (self.product, self.vendor)

    class Meta:
        ordering = ['vendor', 'product']
    
    class Exporter:
        export_fields = ['__all__', '-product']

models.signals.post_save.connect(cache.invalidate_model_handler, sender=VendorProduct)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=VendorProduct)


LOOK_COMPONENT_TYPES = (
    ('C', 'Collage'),
    ('P', 'Picture'),
)

LOOK_COMPONENT_POSITIONED = (
    ('A', 'Automatically'),
    ('M', 'Manually'),
)

class VendorProductVariation(models.Model):
    """
    This class represents product combinations sold at a particular vendor
    """
    vendor_product = models.ForeignKey(VendorProduct, related_name='variations')
    # Negative value means it is in stock, but we have no information about how many
    # Null means we have no information about availability
    # 0 means it is sold out
    in_stock = models.IntegerField(_('Items in stock'), null=True, blank=True)
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

models.signals.post_save.connect(cache.invalidate_model_handler, sender=VendorProductVariation)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=VendorProductVariation)


class Look(models.Model):
    title = models.CharField(_('Title'), max_length=200)
    slug  = AutoSlugField(_('Slug Name'), populate_from=("title",), blank=True,
                help_text=_('Used for URLs, auto-generated from name if blank'), max_length=80)
    description = models.TextField(_('Look description'), null=True, blank=True)
    products    = models.ManyToManyField(Product)
    user        = models.ForeignKey(User)
    image       = models.ImageField(upload_to=settings.APPAREL_LOOK_IMAGE_ROOT, max_length=255, blank=True)
    created     = models.DateTimeField(_("Time created"), auto_now_add=True)
    modified    = models.DateTimeField(_("Time modified"), auto_now=True)
    tags        = TagField(blank=True)
    component   = models.CharField(_('What compontent to show'), max_length=1, choices=LOOK_COMPONENT_TYPES, blank=True)
    is_featured = models.BooleanField(default=False, help_text=_('The look will be shown on the front page'))
    
    
    objects  = SearchManager()
    featured = FeaturedManager()
    
    def score(self):
        return Vote.objects.get_score(self)

    def total_price(self, component=None):
        """
        Returns the total price of the given component, or default if none specified
        To get the price of all components, specify A
        """
        
        components = None
        
        if component == 'C':
            components = self.collage_components
        elif components == 'P':
            components = self.photo_components
        elif components == 'A':
            components = self.components
        else:
            components = self.display_components
        
        return components.annotate(price=Min('product__vendorproduct__price')).aggregate(Sum('price'))['price__sum']
    
    
    @property
    def photo_components(self):
        """
        All components in the photo view
        """
        return self.components.filter(component_of='P')
    
    @property
    def collage_components(self):
        """
        All components in the collage view
        """
        
        return self.components.filter(component_of='C')
    
    @property
    def display_components(self):
        """
        All components in the view that should be displayed according to the
        logic in "display_with_component"
        """
        
        return self.photo_components if self.display_with_component == 'P' else self.collage_components
    
    @property
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
    
    def __unicode__(self):
        return u"%s by %s" % (self.title, self.user)
    
    @models.permalink
    def get_absolute_url(self):
        return ('apparel.views.look_detail', [str(self.slug)])
    
    class Meta:
        ordering = ['user', 'title']

    class Exporter:
        export_fields = ['__all__', 'get_absolute_url', 'photo_components', 'display_with_component', 'collage_components', 'score']

models.signals.post_save.connect(cache.invalidate_model_handler, sender=Look)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=Look)

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
        return self._style(93 / 694.0)

    @property
    def style_middle(self):
        return self._style(450 / 694.0)

    @property
    def style(self):
        return self._style(1)
    
    def save(self, *args, **kwargs):
        if self.component_of == 'C' and self.product.product_image and not self.height and not self.width:
            # This scales collage images to maximum size if height and width isn't defined
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
        export_fields = ['__all__', 'style', 'style_middle', 'style_small', '-look']

models.signals.post_save.connect(cache.invalidate_model_handler, sender=LookComponent)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=LookComponent)

class Wardrobe(models.Model):
    user     = models.ForeignKey(User)
    products = models.ManyToManyField(Product)
    
    def __unicode__(self):
        return u'Wardrobe for %s' % self.user

class FirstPageContent(models.Model):
    title     = models.CharField(_('Title'), max_length=127, blank=True)
    content   = models.TextField(_('Content'), null=True, blank=True, help_text=_('HTML allowed'))
    url       = models.URLField(_('URL'), max_length=255, null=True, blank=True,)
    image     = models.ImageField(_('Image'), upload_to=settings.APPAREL_MISC_IMAGE_ROOT, max_length=255, null=True, blank=True, help_text=_('Publish size 450x327'))
    published = models.BooleanField(default=False)
    pub_date  = models.DateTimeField(_("Publish date"))
    created   = models.DateTimeField(_("Time created"), auto_now_add=True)
    modified  = models.DateTimeField(_("Time modified"), auto_now=True)

    objects = models.Manager()
    published_objects = FirstPageManager()

    def __unicode__(self):
        return u'%s' % (self.title,)

    class Meta:
        ordering = ['-pub_date']

models.signals.post_save.connect(cache.invalidate_model_handler, sender=FirstPageContent)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=FirstPageContent)

import apparel.activity
