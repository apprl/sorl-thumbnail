from django.db import models
from django.utils import timezone


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

    def __unicode__(self):
        return u'%s' % (self.name,)


class BrandMapping(BaseModel):
    vendor = models.ForeignKey('theimp.Vendor', null=False, blank=False)
    brand = models.CharField(max_length=512)
    mapped_brand = models.CharField(max_length=512)

    def __unicode__(self):
        if self.mapped_brand:
            return u'%s: "%s" mapped to "%s"' % (self.vendor_id, self.brand, self.mapped_brand)

        return '%s: "%s" is unmapped' % (self.vendor_id, self.brand,)


class CategoryMapping(BaseModel):
    vendor = models.ForeignKey('theimp.Vendor', null=False, blank=False)
    category = models.CharField(max_length=512)
    mapped_category = models.CharField(max_length=512)

    def __unicode__(self):
        if self.mapped_category:
            return '%s: "%s" mapped to "%s"' % (self.vendor_id, self.category, self.mapped_category)

        return '%s: "%s" is unmapped' % (self.vendor_id, self.category,)
