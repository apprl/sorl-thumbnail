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

    is_auto_validated = models.NullBooleanField(default=None, null=True, blank=True)
    is_manual_validated = models.NullBooleanField(default=None, null=True, blank=True)
    merged = models.ForeignKey('theimp.Product', null=True, blank=True)

    def __unicode__(self):
        return 'Product(key=%s)' % (self.key,)


class BrandMapping(BaseModel):
    brand = models.CharField(max_length=512)
    mapped_brand = models.CharField(max_length=512)


class CategoryMapping(BaseModel):
    category = models.CharField(max_length=512)
    mapped_category = models.CharField(max_length=512)
