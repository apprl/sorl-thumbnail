import string

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from mptt.models import TreeForeignKey


class BaseModel(models.Model):
    created = models.DateTimeField(default=timezone.now, null=False, blank=False)
    modified = models.DateTimeField(default=timezone.now, null=False, blank=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        super(BaseModel, self).save(*args, **kwargs)


class Product(BaseModel):
    key = models.CharField(max_length=512)
    vendor = models.ForeignKey('theimp.Vendor', null=False, blank=False)
    json = models.TextField()

    is_dropped = models.BooleanField(default=False, null=False, blank=False)
    is_validated = models.NullBooleanField(default=None, null=True, blank=True)

    brand_mapping = models.ForeignKey('theimp.BrandMapping', related_name='products', null=True)
    category_mapping = models.ForeignKey('theimp.CategoryMapping', related_name='products', null=True)

    parsed_date = models.DateTimeField(null=True, blank=True)
    imported_date = models.DateTimeField(null=True, blank=True)

    is_released = models.BooleanField(default=False, null=False, blank=False)

    def __unicode__(self):
        return 'Product(key=%s)' % (self.key,)


class Vendor(BaseModel):
    name = models.CharField(max_length=128)
    affiliate_identifier = models.CharField(max_length=128, null=True, blank=True)
    is_active = models.BooleanField(default=True, null=False, blank=False)
    comment  = models.TextField(blank=True, default='')
    vendor = models.ForeignKey('apparel.Vendor', null=True, blank=True)

    last_imported_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return u'%s' % (self.name,)

    def __repr__(self):
        return ('Vendor(%s)' % (self.name,)).encode('utf-8')

    def to_json(self):
        import simplejson
        assigned_timezone = timezone.get_current_timezone()
        fmt = '%Y-%m-%d %H:%M:%S %Z%z'
        return simplejson.dumps({
            "id":self.id,
            "name":self.name,
            "affiliate_identifier":self.affiliate_identifier,
            "is_active":self.is_active,
            "comment":self.comment,
            "apprl_vendor":self.vendor.name if self.vendor else None,
            "apprl_vendor_id":self.vendor_id,
            "last_imported_date": assigned_timezone.localize(self.last_imported_date).strftime(fmt) if self.last_imported_date else None,
            "created": assigned_timezone.localize(self.created).strftime(fmt) if self.created else None,
            "modified": assigned_timezone.localize(self.modified).strftime(fmt) if self.modified else None,
        })

    class Meta:
        ordering = ('name',)


class BrandMapping(BaseModel):
    vendor = models.ForeignKey('theimp.Vendor', null=False, blank=False)
    brand = models.CharField(max_length=1024)
    mapped_brand = models.ForeignKey('apparel.Brand', null=True, blank=True)

    def __unicode__(self):
        if self.mapped_brand:
            return u'%s: "%s" mapped to "%s"' % (self.vendor_id, self.brand, self.mapped_brand)

        return '%s: "%s" is unmapped' % (self.vendor_id, self.brand)

    def to_json(self):
        import simplejson
        assigned_timezone = timezone.get_current_timezone()
        fmt = '%Y-%m-%d %H:%M:%S %Z%z'
        return simplejson.dumps({
            "id":self.id,
            "vendor_id":self.vendor_id,
            "brand":self.brand,
            "apparel_mapped_brand_id":self.mapped_brand_id,
            "created": assigned_timezone.localize(self.created).strftime(fmt) if self.created else None,
            "modified": assigned_timezone.localize(self.modified).strftime(fmt) if self.modified else None,
        })

class CategoryMapping(BaseModel):
    vendor = models.ForeignKey('theimp.Vendor', null=False, blank=False)
    category = models.CharField(max_length=1024)
    mapped_category = TreeForeignKey('apparel.Category', null=True, blank=True)

    def __unicode__(self):
        if self.mapped_category:
            return '%s: "%s" mapped to "%s"' % (self.vendor_id, self.category, self.mapped_category)

        return '%s: "%s" is unmapped' % (self.vendor_id, self.category)

    def to_json(self):
        import simplejson
        assigned_timezone = timezone.get_current_timezone()
        fmt = '%Y-%m-%d %H:%M:%S %Z%z'
        return simplejson.dumps({
            "id":self.id,
            "vendor_id":self.vendor_id,
            "category":self.category,
            "apparel_mapped_category_id":self.mapped_category_id,
            "created": assigned_timezone.localize(self.created).strftime(fmt) if self.created else None,
            "modified": assigned_timezone.localize(self.modified).strftime(fmt) if self.modified else None,
        })


MAPPING_CHOICES = (
    ('color', 'color'),
    ('pattern', 'pattern'),
    ('gender', 'gender'),
)

class Mapping(models.Model):
    mapping_type = models.CharField(max_length=24, choices=MAPPING_CHOICES, null=False, blank=False)
    mapping_key = models.CharField(max_length=100, unique=True, null=False, blank=False)
    mapping_aliases = models.TextField(null=False, blank=False,
            help_text=_('Mapping aliases should be separated with a single command and no spaces, example: "svart,night,coal"'))

    def get_list(self):
        return map(string.strip, self.mapping_aliases.split(','))

    def __unicode__(self):
        return u'%s: %s' % (self.mapping_key, self.mapping_aliases)

    def to_json(self):
        import simplejson
        return simplejson.dumps({
            "id":self.id,
            "mapping_type":self.mapping_type,
            "mapping_key":self.mapping_key,
            "mapping_aliases":self.mapping_aliases,
        })