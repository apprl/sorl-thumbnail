from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

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
    json = models.TextField()

    dropped = models.BooleanField(default=False, null=False, blank=False)
    is_auto_validated = models.NullBooleanField(default=None, null=True, blank=True)
    is_manual_validated = models.NullBooleanField(default=None, null=True, blank=True)
    merged = models.ForeignKey('theimp.Product', null=True, blank=True)
    vendor = models.ForeignKey('theimp.Vendor', null=False, blank=False)

    def __unicode__(self):
        return 'Product(key=%s)' % (self.key,)


class Vendor(BaseModel):
    name = models.CharField(max_length=128)
    affiliate_identifier = models.CharField(max_length=128, null=True, blank=True)
    is_active = models.BooleanField(default=True, null=False, blank=False)
    comment  = models.TextField(blank=True, default='')
    vendor = models.ForeignKey('apparel.Vendor', null=True, blank=True)

    def __unicode__(self):
        return u'%s' % (self.name,)

    def __repr__(self):
        return ('Vendor(%s)' % (self.name,)).encode('utf-8')


class BrandMapping(BaseModel):
    vendor = models.ForeignKey('theimp.Vendor', null=False, blank=False)
    brand = models.CharField(max_length=1024)
    mapped_brand = models.ForeignKey('apparel.Brand', null=True, blank=True)

    def __unicode__(self):
        if self.mapped_brand:
            return u'%s: "%s" mapped to "%s"' % (self.vendor_id, self.brand, self.mapped_brand)

        return '%s: "%s" is unmapped' % (self.vendor_id, self.brand)


class CategoryMapping(BaseModel):
    vendor = models.ForeignKey('theimp.Vendor', null=False, blank=False)
    category = models.CharField(max_length=1024)
    mapped_category = models.ForeignKey('apparel.Category', null=True, blank=True)

    def __unicode__(self):
        if self.mapped_category:
            return '%s: "%s" mapped to "%s"' % (self.vendor_id, self.category, self.mapped_category)

        return '%s: "%s" is unmapped' % (self.vendor_id, self.category)


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
        return self.mapping_aliases.split(',')

    def __unicode__(self):
        return u'%s: %s' % (self.mapping_key, self.mapping_aliases)
