import logging
import uuid
import os.path
import decimal
import datetime

from django.db import models
from django.db.models import Sum, Min
from django.contrib.auth.models import User
from django.utils.translation import get_language, ugettext_lazy as _
from django.template.defaultfilters import slugify
from django.conf import settings
from django.forms import ValidationError

from apparel.manager import SearchManager, FeaturedManager, FirstPageManager
from apparel import cache

from tagging.fields import TagField
from sorl.thumbnail import ImageField
from sorl.thumbnail import get_thumbnail
from django_extensions.db.fields import AutoSlugField
from mptt.models import MPTTModel, TreeForeignKey
from mptt.managers import TreeManager

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
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'

    class Exporter:
        export_fields = ['__all__', '-active']


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
    name     = models.CharField(max_length=100, db_index=True)
    homepage = models.URLField(_('Home page'))
    logotype = models.ImageField(upload_to=settings.APPAREL_LOGO_IMAGE_ROOT, help_text=_('Logotype'), max_length=127, blank=True, null=True) 

    objects = SearchManager()

    class Meta:
        ordering = ['name']
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __unicode__(self):
        return u"%s" % self.name

class Category(MPTTModel):
    name          = models.CharField(max_length=100, db_index=True)
    name_order    = models.CharField(max_length=100, null=True, blank=True)
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

models.signals.post_save.connect(cache.invalidate_model_handler, sender=Category)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=Category)

PRODUCT_GENDERS = (
    ('W', 'Women',),
    ('M', 'Men',),
    ('U', 'Unisex',),
)



class Product(models.Model):
    manufacturer = models.ForeignKey(Manufacturer)
    category = TreeForeignKey(Category, blank=True, null=True)
    options  = models.ManyToManyField(Option,   blank=True, verbose_name=_("Option"))
    slug = AutoSlugField(_("Slug Name"), populate_from=("manufacturer", "product_name",), blank=True,
        help_text=_("Used for URLs, auto-generated from name if blank"), max_length=80)
    sku = models.CharField(_("Stock Keeping Unit"), max_length=255, blank=False, null=False,
        help_text=_("Has to be unique with the manufacturer"))
    product_name  = models.CharField(max_length=200, null=True, blank=True)
    date_added    = models.DateTimeField(_("Time added"), null=True, blank=True, db_index=True)
    modified      = models.DateTimeField(_("Time modified"), null=True, auto_now=True)
    description   = models.TextField(_('Product description'), null=True, blank=True)
    product_image = ImageField(upload_to=settings.APPAREL_PRODUCT_IMAGE_ROOT, max_length=255, help_text=_('Product image'))
    vendors       = models.ManyToManyField(Vendor, through='VendorProduct')
    # FIXME: Could we have ForeignKey to VendorProduct instead?
    gender        = models.CharField(_('Gender'), max_length=1, choices=PRODUCT_GENDERS, null=True, blank=True, db_index=True)
    feed_gender   = models.CharField(_('Feed gender'), max_length=1, choices=PRODUCT_GENDERS, null=True, blank=True, db_index=True)
    published     = models.BooleanField(default=True, db_index=True)
    popularity    = models.DecimalField(default=0, max_digits=20, decimal_places=8)
    
    objects = SearchManager()
    
    def score(self):
        return ProductLike.objects.filter(product=self, active=True).count()

    @property
    def default_vendor(self):
        if not hasattr(self, '_default_vendor'):
            try:
                self._default_vendor = self.vendorproduct.order_by('price')[0]
            except IndexError:
                self._default_vendor = None

        return self._default_vendor

    @property
    def original_currency(self):
        if not hasattr(self, '_original_currency'):
            self._original_currency = []
            for vendorproduct in self.vendorproduct.all():
                if vendorproduct.original_currency != 'SEK':
                    self._original_currency.append(vendorproduct.original_currency)

        return self._original_currency

    @models.permalink
    def get_absolute_url(self):
        return ('apparel.views.product_detail', [str(self.slug)])

    @property
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

    @property
    def colors(self):
        return self.options.filter(option_type__name='color').values_list('value', flat=True)
    
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
        ordering = ('-id',)
    
    class Exporter:
        export_fields = ['__all__', 'get_absolute_url', 'default_vendor', 'score']

models.signals.post_save.connect(cache.invalidate_model_handler, sender=Product)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=Product)

def delete_product_likes(sender, instance, **kwargs):
    """
    Delete all likes for the sender.
    """
    ProductLike.objects.filter(product=instance).delete()

models.signals.post_delete.connect(delete_product_likes, sender=Product)

class ProductLike(models.Model):
    """
    Keep track of likes on products
    """
    product = models.ForeignKey(Product, related_name='likes')
    user = models.ForeignKey(User, related_name='product_likes')
    created = models.DateTimeField(_("Time created"), auto_now_add=True, null=True, blank=True)
    modified = models.DateTimeField(_("Time modified"), auto_now=True, null=True, blank=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return u'%s likes product %s' % (self.user, self.product)

    class Meta:
        unique_together = (('product', 'user'),)

# Maps products for a specific vendor 
# This is used for importing stuff - when this category is changed,
# all related products will be updated to reflect the category
class VendorCategory(models.Model):
    category = TreeForeignKey(Category, verbose_name=_('category'), blank=True, null=True)
    name     = models.CharField(_('Name'), max_length=555)
    vendor   = models.ForeignKey(Vendor)
    default_gender = models.CharField(_('Default gender'), max_length=1, choices=PRODUCT_GENDERS, null=True, blank=True)
    override_gender = models.CharField(_('Override gender'), max_length=1, choices=PRODUCT_GENDERS, null=True, blank=True)
    
    # Update all related products to point to the category
    def save(self, *args, **kwargs):
        if self.category:
            queryset = Product.objects.filter(vendorproduct__vendor_category=self)
            for product in queryset:
                product.category = self.category
                product.published = True
                product.save()
        else:
            queryset = Product.objects.filter(vendorproduct__vendor_category=self, category__isnull=False)
            for product in queryset:
                product.category = None
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


class VendorProduct(models.Model):
    vendor            = models.ForeignKey(Vendor)
    product           = models.ForeignKey(Product, related_name='vendorproduct')
    vendor_category   = models.ForeignKey(VendorCategory, related_name='vendorproducts', null=True,)
    buy_url           = models.URLField(_('Buy URL'), null=True, blank=True, max_length=555,)
    price             = models.DecimalField(_('Price'), null=True, blank=True, max_digits=10, decimal_places=2, db_index=True, help_text=_('Price converted to base currency'))
    currency          = models.CharField(_('Currency'), null=True, blank=True, max_length=3, help_text=_('Base currency as three-letter ISO code'))
    original_price    = models.DecimalField(_('Original price'), null=True, blank=True, max_digits=10, decimal_places=2,)
    original_currency = models.CharField(_('Original currency'), null=True, blank=True, max_length=3, help_text=_('Currency as three-letter ISO code'))
    discount_price    = models.DecimalField(_('Discount price'), null=True, blank=True, max_digits=10, decimal_places=2)
    discount_currency = models.CharField(_('Discount currency'), null=True, blank=True, max_length=3, help_text=_('Currency as three-letter ISO code'))
    original_discount_price = models.DecimalField(_('Original discount price'), null=True, blank=True, max_digits=10, decimal_places=2)
    original_discount_currency = models.CharField(_('Original discount currency'), null=True, blank=True, max_length=3, help_text=_('Currency as three-letter ISO code'))
    availability  = models.IntegerField(_('Items in stock'), null=True, blank=True, help_text=_('Negative value means it is in stock, but we have no information about how many. Null means we have no information about availability. 0 means it is sold out'))

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

models.signals.post_save.connect(cache.invalidate_model_handler, sender=VendorProductVariation)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=VendorProductVariation)

def look_image_path(instance, filename):
    return os.path.join(settings.APPAREL_LOOK_IMAGE_ROOT, uuid.uuid4().hex)

def validate_not_spaces(value):
    if value.strip() == '':
        raise ValidationError(u'You must provide more than just whitespace.')

class Look(models.Model):
    title = models.CharField(_('Title'), max_length=200, validators=[validate_not_spaces])
    slug  = AutoSlugField(_('Slug Name'), populate_from=("title",), blank=True,
                help_text=_('Used for URLs, auto-generated from name if blank'), max_length=80)
    description = models.TextField(_('Look description'), null=True, blank=True)
    user        = models.ForeignKey(User)
    image       = ImageField(upload_to=look_image_path, max_length=255, blank=True)
    created     = models.DateTimeField(_("Time created"), auto_now_add=True)
    modified    = models.DateTimeField(_("Time modified"), auto_now=True)
    tags        = TagField(blank=True)
    component   = models.CharField(_('What compontent to show'), max_length=1, choices=LOOK_COMPONENT_TYPES, blank=True)
    is_featured = models.BooleanField(default=False, help_text=_('The look will be shown on the front page'))
    gender      = models.CharField(_('Gender'), max_length=1, choices=PRODUCT_GENDERS, null=False, blank=False, default='U')
    
    
    objects  = SearchManager()
    featured = FeaturedManager()

    def save(self, *args, **kwargs):
        self.gender = self.calculate_gender()
        super(Look, self).save(*args, **kwargs)

    def calculate_gender(self):
        """
        Calculate looks gender based on displayed products.

        Implementation uses set difference which result in a set with either
        Man, Woman or Man & Woman.
        """
        unique_genders = set(self.display_components.values_list('product__gender', flat=True))
        unique_genders = list(unique_genders - set('U'))
        if len(unique_genders) == 1:
            return unique_genders[0]

        return 'U'
    
    def score(self):
        return LookLike.objects.filter(look=self, active=True).count()

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

        total = decimal.Decimal('0.00')
        for component in components:
            if component.product.default_vendor:
                if component.product.default_vendor.discount_price:
                    total += component.product.default_vendor.discount_price
                else:
                    total += component.product.default_vendor.price

        return total
        #return components.annotate(price=Min('product__vendorproduct__price')).aggregate(Sum('price'))['price__sum']
    
    
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

    @property
    def product_manufacturers(self):
        return self.display_components.values_list('product__manufacturer__name', flat=True)
    
    def __unicode__(self):
        return u"%s by %s" % (self.title, self.user.get_profile().display_name)
    
    @models.permalink
    def get_absolute_url(self):
        return ('apparel.views.look_detail', [str(self.slug)])
    
    class Meta:
        ordering = ['user', 'title']

    class Exporter:
        export_fields = ['__all__', 'get_absolute_url', 'photo_components', 'display_with_component', 'collage_components', 'score']

models.signals.post_save.connect(cache.invalidate_model_handler, sender=Look)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=Look)

def delete_look_likes(sender, instance, **kwargs):
    """
    Delete all likes for the sender.
    """
    LookLike.objects.filter(look=instance).delete()

models.signals.post_delete.connect(delete_look_likes, sender=Look)

class LookLike(models.Model):
    """
    Keep track of likes on looks
    """
    look = models.ForeignKey(Look, related_name='likes')
    user = models.ForeignKey(User, related_name='look_likes')
    created = models.DateTimeField(_("Time created"), auto_now_add=True, null=True, blank=True)
    modified = models.DateTimeField(_("Time modified"), auto_now=True, null=True, blank=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return u'%s likes look %s' % (self.user, self.look)

    class Meta:
        unique_together = (('look', 'user'),)

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
            thumb = get_thumbnail(self.product.product_image, '%sx%s' % (settings.APPAREL_LOOK_MAX_SIZE, settings.APPAREL_LOOK_MAX_SIZE), crop='noop', quality=99)
            self.width = thumb.width
            self.height = thumb.height

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
    products = models.ManyToManyField(Product, through='WardrobeProduct')

    def __unicode__(self):
        return u'Wardrobe for %s' % self.user.get_profile().display_name

class WardrobeProduct(models.Model):
    """
    Maps the relation between products and a users wardrobe, with the addition
    of creation time.
    """
    created  = models.DateTimeField(_("Time created"), auto_now_add=True)
    wardrobe = models.ForeignKey(Wardrobe)
    product = models.ForeignKey(Product)

    class Meta:
        db_table = 'apparel_wardrobe_products'

class FirstPageContent(models.Model):
    title       = models.CharField(_('Title'), max_length=127, blank=True)
    description = models.TextField(_('Short description'), null=True, blank=True)
    content     = models.TextField(_('Content'), null=True, blank=True, help_text=_('HTML allowed. This field is ignored if an image is set.'))
    url         = models.URLField(_('URL'), max_length=255, null=True, blank=True,)
    image       = ImageField(_('Image'), upload_to=settings.APPAREL_MISC_IMAGE_ROOT, max_length=255, null=True, blank=True, help_text=_('Publish size 450x327'))
    published   = models.BooleanField(default=False)
    pub_date    = models.DateTimeField(_("Publish date"))
    created     = models.DateTimeField(_("Time created"), auto_now_add=True)
    modified    = models.DateTimeField(_("Time modified"), auto_now=True)
    gender      = models.CharField(_('Gender'), max_length=1, choices=PRODUCT_GENDERS, default='U', null=False, blank=False)
    language    = models.CharField(_('Language'), max_length=3, choices=settings.LANGUAGES, null=False, blank=False, default='sv')
    sorting     = models.PositiveIntegerField(_('Sorting order'), default=0, null=False, blank=False)


    objects = models.Manager()
    published_objects = FirstPageManager()

    def __unicode__(self):
        return u'%s' % (self.title,)

    class Meta:
        ordering = ['sorting', '-pub_date']

models.signals.post_save.connect(cache.invalidate_model_handler, sender=FirstPageContent)
models.signals.post_delete.connect(cache.invalidate_model_handler, sender=FirstPageContent)

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

def save_synonym_file(sender, **kwargs):
    instance = kwargs['instance']
    synonym_file = open(settings.SEARCH_SYNONYM_FILE, "w")
    synonym_file.write(instance.content.encode("utf-8"))
    synonym_file.close()

    # FIXME: Move this link to a config file
    import requests
    requests.get('http://localhost:8983/solr/admin/cores?action=RELOAD&core=collection1')

class SynonymFile(models.Model):
    content = models.TextField(_('Synonyms'), null=True, blank=True, help_text=_('Place all synonyms on their own line, comma-separated. Comments start with "#".'))

    def __unicode__(self):
        return u'%s...' % (self.content[0:20],)

    def clean(self):
        if not hasattr(settings, "SEARCH_SYNONYM_FILE"):
            raise ValidationError("You must define the SEARCH_SYNONYM_FILE before using synonyms.")

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

import apparel.activity
