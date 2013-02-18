from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

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
    product = models.CharField(max_length=100)
    vendor = models.CharField(max_length=100)
    price = models.IntegerField()
    user_id = models.IntegerField(default=0, null=True, blank=True)
    page = models.CharField(max_length=50, null=True, blank=True)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=False, blank=False)
    referer = models.TextField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    ip = models.GenericIPAddressField()

    class Meta:
        ordering = ['-created']


class NotificationEmailStats(models.Model):
    notification_name = models.CharField(max_length=50)
    notification_count = models.IntegerField()
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=False, blank=False)

    class Meta:
        ordering = ['notification_name']
