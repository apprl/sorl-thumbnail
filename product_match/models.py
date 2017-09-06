from django.db import models

#import theimp
from apparelrow.apparel.models import Product
from django.utils.translation import get_language, ugettext_lazy as _


# Create your models here.
class Url(models.Model):
    product = models.ForeignKey("apparel.Product", null=True, blank=True)
    product = models.ForeignKey('theimp.Product.product', related_name='url_products', blank=False, null=False)
    url = models.CharField(max_length=512, null=True, blank=True)
    domain = models.CharField(max_length=500, null=True, blank=True)
    path = models.CharField(max_length=500, null=True, blank=True)
    query = models.CharField(max_length=500, null=True, blank=True)
    fragment = models.CharField(max_length=505, null=True, blank=True)
    parameters = models.CharField(max_length=500, null=True, blank=True)
    created = models.DateTimeField(_("Time added"), null=True, blank=True, db_index=True)
    modified = models.DateTimeField(_("Time modified"), null=True, auto_now=True)
