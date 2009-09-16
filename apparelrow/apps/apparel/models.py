from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import get_language, ugettext_lazy as _
from django.template.defaultfilters import slugify
import datetime
import mptt

class Manufacturer(models.Model):
    name = models.CharField(max_length=50)
    active = models.BooleanField(default=False, help_text=_("Products can only be displayed for an active manufactorer"))
    def __unicode__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')
    active = models.BooleanField(default=False, help_text=_('Only active categories are visible and searchable on the website'))
    def __unicode__(self):
        return self.name

try:
    mptt.register(Category, order_insertion_by=['name'])
except mptt.AlreadyRegistered:
    # FIXME: Use a debug statement here
    print "Attempt to register category, but it's already registered"
    

class Product(models.Model):
    GENDER_CHOICES = (
        ('F', 'Female'),
        ('M', 'Male'),
        ('U', 'Unisex'),
    )
    manufacturer = models.ForeignKey(Manufacturer)
    slug = models.SlugField(_("Slug Name"), blank=True,
        help_text=_("Used for URLs, auto-generated from name if blank"), max_length=80)
    sku = models.CharField(_("Stock Keeping Unit"), max_length=255, blank=True, null=True,
        help_text=_("Defaults to slug if left blank"))
    category = models.ManyToManyField(Category, blank=True, verbose_name=_("Category"))
    product_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_added = models.DateField(_("Date added"), null=True, blank=True)

    def __unicode__(self):
        return "%s %s %s" % (self.manufacturer, self.product_name, self.category)

    def save(self, force_insert=False, force_update=False):
        if not self.pk:
            self.date_added = datetime.date.today()

        if self.product_name and not self.slug:
            self.slug = slugify(self.product_name)

        if not self.sku:
            self.sku = self.slug
        super(Product, self).save(force_insert=force_insert, force_update=force_update)

class OptionGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=100)
    sort_order = models.IntegerField()

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = _("Option Group")
        verbose_name_plural = _("Option Groups")

class Option(models.Model):
    option_group = models.ForeignKey(OptionGroup)
    # FIXME:
    # It might be good to add a value field for a couple of different datatypes
#    value_str  = models.CharField(_('Text value'), max_length=255)
#    value_int  = models.CharField(_('Integer value'), max_length=255)
    value = models.CharField(_('Value'), max_length=255)
    sort_order = models.IntegerField(_('Sort order'))

    class Meta:
        ordering = ['option_group', 'sort_order']
        unique_together = (('option_group', 'value'),)
        verbose_name = _('Option Item')
        verbose_name_plural = _('Option Items')

class ConfiguredProduct(models.Model):
    product = models.ForeignKey(Product, primary_key=True)
    option_group = models.ManyToManyField(OptionGroup, blank=True, verbose_name=_('Option Group'))

class Look(models.Model):
    title = models.CharField(max_length=200)
    products = models.ManyToManyField(Product)
    user = models.ForeignKey(User)
    image = models.ImageField(upload_to='looks')

    def __unicode__(self):
        return "%s by %s" % (self.title, self.user)

