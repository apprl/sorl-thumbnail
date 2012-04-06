from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist

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
