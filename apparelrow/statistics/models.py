from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from apparelrow.apparel.tasks import product_popularity
from apparelrow.apparel.models import Product
from apparelrow.statistics.utils import get_country_by_ip_string

import logging
logger = logging.getLogger( __name__ )


PERIOD_TYPES = (
    ('D', 'Daily'),
    ('W', 'Weekly'),
    ('M', 'Monthly'),
)

class ActiveUser(models.Model):
    period_type = models.CharField(max_length=1, choices=PERIOD_TYPES, null=False, blank=False, default='D')
    period_key = models.CharField(max_length=24)
    period_value = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-period_key']

class ProductClickManager(models.Manager):

    def increment_clicks(self, product_id, increment_by=1):
        """
        Increment the click count for an URL.
        """
        if product_id:
            content_type = ContentType.objects.get_by_natural_key('apparel', 'product')
            try:
                product = content_type.get_object_for_this_type(pk=product_id)
                click, created = self.get_or_create(product=product, defaults={'click_count': increment_by})
                if not created:
                    click.click_count += increment_by
                    click.save()

                product_popularity.delay(product)

                return click.click_count
            except ObjectDoesNotExist:
                pass


class ProductClick(models.Model):
    product = models.ForeignKey('apparel.Product')
    click_count = models.PositiveIntegerField(default=0)

    objects = ProductClickManager()

    def __unicode__(self):
        return u'%s with %s clicks' % (self.product.product_name, self.click_count)

    class Meta:
        verbose_name = _(u'Product clicks')
        verbose_name_plural = _(u'Product clicks')
        ordering = ['-click_count']


class ProductStat(models.Model):
    action = models.CharField(max_length=50)
    product = models.CharField(max_length=100, null=True, blank=True)
    vendor = models.CharField(max_length=100, null=True, blank=True)
    price = models.IntegerField(null=True, blank=True)
    user_id = models.IntegerField(default=0, null=True, blank=True)
    page = models.CharField(max_length=50, null=True, blank=True)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=False, blank=False)
    referer = models.TextField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    ip = models.GenericIPAddressField()
    is_valid = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created']

@receiver(post_save, sender=ProductStat, dispatch_uid='productstat_post_save')
def productstat_post_save(sender, instance, created, **kwargs):
    if created:
        try:
            product = Product.objects.get(slug=instance.product)
            if product.default_vendor and product.default_vendor.vendor.is_cpc:
                country = get_country_by_ip_string(instance.ip)
                if country:
                    vendor_markets = settings.VENDOR_LOCATION_MAPPING.get(product.default_vendor.vendor.name, None)
                    if not country in vendor_markets:
                        instance.is_valid = False
                        instance.save()
                else:
                    instance.is_valid = False
                    instance.save()
        except Product.DoesNotExist:
            logger.warning("Product %s does not exist" % instance.product)


class NotificationEmailStats(models.Model):
    notification_name = models.CharField(max_length=50)
    notification_count = models.IntegerField()
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=False, blank=False)

    class Meta:
        ordering = ['notification_name']
