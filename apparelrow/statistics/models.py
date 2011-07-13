from django.db import models
from django.utils.translation import ugettext_lazy as _

from apparelrow.apparel.models import Product

class ProductClickManager(models.Manager):

    def increment_clicks(self, product_id, increment_by=1):
        """
        Increment the click count for an URL.
        """
        if product_id:
            click, created = self.get_or_create(product=Product.objects.get(pk=product_id), defaults={'click_count': increment_by})
            if not created:
                click.click_count += increment_by
                click.save()

            return click.click_count

class ProductClick(models.Model):
    product = models.ForeignKey(Product)
    click_count = models.PositiveIntegerField(default=0)

    objects = ProductClickManager()

    def __unicode__(self):
        return u'%s with %s clicks' % (self.product.product_name, self.click_count)

    class Meta:
        verbose_name = _(u'Product clicks')
        verbose_name_plural = _(u'Product clicks')
        ordering = ['-click_count']
