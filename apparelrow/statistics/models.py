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
from apparelrow.apparel.utils import decompress_source_link_if_needed
from apparelrow.statistics.utils import get_country_by_ip_string, is_ip_banned, check_contains_invalid_user_agents

import logging
logger = logging.getLogger( "apparelrow" )


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
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=False, blank=False, db_index=True)
    referer = models.TextField(null=True, blank=True)
    source_link = models.CharField(max_length=512, null=True, blank=True)  # NOTE: concatination issues here???
    user_agent = models.TextField(null=True, blank=True)
    ip = models.GenericIPAddressField()
    is_valid = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created']
        index_together = [['created', 'user_id']]

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.source_link = decompress_source_link_if_needed(self.source_link)
        super(ProductStat, self).save(force_insert, force_update, using, update_fields)

    def __unicode__(self):
        return u'action: %s product: %s source_link: %s vendor: %s user_id: %s created: %s' % (self.action, self.product, self.source_link, self.vendor, self.user_id, self.created)


@receiver(post_save, sender=ProductStat, dispatch_uid='productstat_post_save')
def productstat_post_save(sender, instance, created, **kwargs):
    """
    Checks if a valid click should be revoked due to the click does not belong to a market that the vendor is shipping to.
    :param sender:
    :param instance:
    :param created:
    :param kwargs:
    :return:
    """

    # Only do this check if the instance is created and the instance is valid. If not valid there is not really any point.
    if created and instance.is_valid:
        if is_ip_banned(instance.ip):
            logger.info("Clicks from this ip {} has been placed in quarantine.".format(instance.ip))
            instance.is_valid = False
            instance.save()
        elif check_contains_invalid_user_agents(instance.user_agent):
            logger.info("Clicks from this user agent {} has been placed in quarantine.".format(instance.user_agent))
            instance.is_valid = False
            instance.save()
        else:
            try:
                product = Product.objects.get(slug=instance.product)
                if product.default_vendor and product.default_vendor.vendor.is_cpc:
                    country = get_country_by_ip_string(instance.ip)

                    vendor_name = product.default_vendor.vendor.name
                    vendor_markets = product.default_vendor.vendor.location_codes_list()

                    logger.info("Click verification: %s belongs to market for vendor %s" % (country, vendor_name))
                    if not vendor_markets or len(vendor_markets) == 0:
                        vendor_markets = settings.DEFAULT_VENDOR_LOCATION
                        logger.info("Click verification: No vendor market entry for vendor %s, falling back on default." % (vendor_name))
                    if country not in vendor_markets:
                        logger.info("%s does not belong to market for vendor %s, %s" % (country, vendor_name,vendor_markets))
                        instance.is_valid = False
                        instance.vendor = vendor_name
                        instance.save()
                    else:
                        logger.info("Click from %s for vendor %s is verified for markets %s." % (instance.ip,vendor_name,vendor_markets))
                else:
                    logger.info("Not running lookup due to default vendor %s not being CPC." % product.default_vendor)
            except Product.DoesNotExist:
                logger.warning("Product %s does not exist" % instance.product)
    else:
        logger.info("Product click is not valid or is not created, no ip check")


class NotificationEmailStats(models.Model):
    notification_name = models.CharField(max_length=50)
    notification_count = models.IntegerField()
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=False, blank=False)

    class Meta:
        ordering = ['notification_name']
