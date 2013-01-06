from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

class Sale(models.Model):
    """
    Sale
    """
    INCOMPLETE = '0'
    DECLINED = '1'
    PENDING = '2'
    CONFIRMED = '3'
    READY = '4' # not used
    PAID = '5' # not used
    STATUS_CHOICES = (
        (INCOMPLETE, 'Incomplete'),
        (DECLINED, 'Declined'),
        (PENDING, 'Pending'),
        (CONFIRMED, 'Confirmed'),
        (READY, 'Ready (payment received)'),
        (PAID, 'Paid'),
    )

    PAID_PENDING = '0'
    PAID_READY = '1'
    PAID_COMPLETE = '2'
    PAID_STATUS_CHOICES = (
        (PAID_PENDING, 'Pending payment'),
        (PAID_READY, 'Ready for payment'),
        (PAID_COMPLETE, 'Payment complete'),
    )

    original_sale_id = models.CharField(max_length=100)
    affiliate = models.CharField(max_length=100, null=False, blank=False)
    vendor = models.ForeignKey('apparel.Vendor', null=True, blank=True, on_delete=models.PROTECT)
    product = models.ForeignKey('apparel.Product', null=True, blank=True, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(null=True, blank=True, default=None)

    user_id = models.PositiveIntegerField(null=True, blank=True)
    placement = models.CharField(max_length=32, null=True, blank=True)

    status = models.CharField(max_length=1, default=INCOMPLETE, choices=STATUS_CHOICES, null=False, blank=False, db_index=True)
    paid = models.CharField(max_length=1, default=PAID_PENDING, choices=PAID_STATUS_CHOICES, null=False, blank=False)
    adjusted = models.BooleanField(null=False, blank=False, default=False)
    adjusted_date = models.DateTimeField(default=None, null=True, blank=True)

    amount = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Sale amount'))
    commission = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Sale commission'))
    currency = models.CharField(null=False, blank=False, default='SEK', max_length=3, help_text=_('Currency as three-letter ISO code'))
    original_amount = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Original sale amount'))
    original_commission = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Original sale commission'))
    original_currency = models.CharField(null=False, blank=False, default='SEK', max_length=3, help_text=_('Original currency as three-letter ISO code'))

    sale_date = models.DateTimeField(_('Time of sale'), default=timezone.now, null=True, blank=True)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(_('Time modified'), default=timezone.now, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        super(Sale, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'%s - %s: %s %s %s' % (self.affiliate, self.vendor.name, self.commission, self.currency, self.status)


class Payment(models.Model):
    user = models.ForeignKey('auth.User', null=False, blank=False, on_delete=models.CASCADE)
    details = models.ForeignKey('profile.PaymentDetail', null=False, blank=False, on_delete=models.CASCADE)
    amount = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Sale amount'))
    paid = models.BooleanField(default=False, null=False, blank=False)
    cancelled = models.BooleanField(default=False, null=False, blank=False)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(_('Time modified'), default=timezone.now, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        super(Payment, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'%s %s' % (self.user, self.amount)

    class Meta:
        ordering = ('-created',)


class Group(models.Model):
    name = models.CharField(max_length=30)

    def __unicode__(self):
        return u'%s' % (self.name,)


class Cut(models.Model):
    group = models.ForeignKey('dashboard.Group', null=False, blank=False, on_delete=models.PROTECT, related_name='cuts')
    vendor = models.ForeignKey('apparel.Vendor', null=False, blank=False, on_delete=models.CASCADE)
    cut = models.DecimalField(null=False, blank=False, default='0.5', max_digits=10, decimal_places=3, help_text=_('Between 1 and 0'))

    def __unicode__(self):
        return u'%s - %s: %s' % (self.group, self.vendor, self.cut)


class Signup(models.Model):
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    blog = models.CharField(max_length=255)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)

    def __unicode__(self):
        return '%s' % (self.name,)
