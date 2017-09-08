from django.db import models

#import theimp
from apparelrow.apparel.models import Product
from django.utils.translation import ugettext_lazy as _


# Create your models here.
class UrlDetail(models.Model):
    product = models.ForeignKey(Product, null=False, blank=False)
    url = models.URLField(max_length=512, null=False, blank=False)
    domain = models.CharField(max_length=512, null=False, blank=False)
    path = models.CharField(max_length=500, null=True, blank=True)
    query = models.CharField(max_length=500, null=True, blank=True)
    fragment = models.CharField(max_length=505, null=True, blank=True)
    created = models.DateTimeField(_("Time added"), null=True, blank=True, db_index=True)
    modified = models.DateTimeField(_("Time modified"), null=True, auto_now=True)


class UrlVendorSpecificParams(models.Model):
    domain = models.CharField(max_length=512, null=False, blank=False)
    parameter_name = models.CharField(max_length=512, null=False, blank=False)
    created = models.DateTimeField(_("Time added"), null=True, blank=True, db_index=True)
    modified = models.DateTimeField(_("Time modified"), null=True, auto_now=True)