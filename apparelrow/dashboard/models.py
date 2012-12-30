from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

class Sale(models.Model):
    """
    Sale
    """
    INCOMPLETE = 'I'
    DECLINED = 'D'
    PENDING = 'P'
    CONFIRMED = 'C'
    READY = 'R'
    PAID = 'A'
    STATUS_CHOICES = (
        (INCOMPLETE, 'Incomplete'),
        (DECLINED, 'Declined'),
        (PENDING, 'Pending'),
        (CONFIRMED, 'Confirmed'),
        (READY, 'Ready (payment received)'),
        (PAID, 'Paid'),
    )

    original_sale_id = models.CharField(max_length=100)
    affiliate = models.CharField(max_length=100, null=False, blank=False)
    vendor = models.ForeignKey('apparel.Vendor', null=True, blank=True, on_delete=models.PROTECT)
    product = models.ForeignKey('apparel.Product', null=True, blank=True, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(null=True, blank=True, default=None)

    user_id = models.PositiveIntegerField(null=True, blank=True)
    placement = models.CharField(max_length=32, null=True, blank=True)

    status = models.CharField(max_length=1, choices=STATUS_CHOICES, null=False, blank=False, db_index=True, default=INCOMPLETE)

    amount = models.DecimalField(null=False, blank=False, max_digits=10, decimal_places=2, help_text=_('Sale amount'))
    commission = models.DecimalField(null=False, blank=False, max_digits=10, decimal_places=2, help_text=_('Sale commission'))
    currency = models.CharField(null=False, blank=False, max_length=3, help_text=_('Base currency as three-letter ISO code'))

    sale_date = models.DateTimeField(_('Time of sale'), default=timezone.now, null=True, blank=True)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(_('Time modified'), default=timezone.now, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        super(Sale, self).save(*args, **kwargs)
