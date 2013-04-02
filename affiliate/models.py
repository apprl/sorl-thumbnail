from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class Store(models.Model):
    identifier = models.CharField(max_length=128, null=False, blank=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, default=None, blank=True, null=True, on_delete=models.SET_NULL, related_name='affiliate_store')
    balance = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)


class Transaction(models.Model):
    ACCEPTED = 'A'
    REJECTED = 'R'
    PENDING = 'P'
    INVALID = 'I'
    TOO_OLD = 'T'
    STATUS_CHOICES = (
        (ACCEPTED, _('Accepted')),
        (REJECTED, _('Rejected')),
        (PENDING, _('Pending')),
        (INVALID, _('Invalid')),
        (TOO_OLD, _('Too old')),
    )

    store_id = models.CharField(max_length=128, null=False, blank=False, db_index=True)
    order_id = models.CharField(max_length=128, null=False, blank=False)
    order_value = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)
    currency = models.CharField(null=False, blank=False, default='SEK', max_length=3, help_text=_('Currency as three-letter ISO code'))

    cookie_date = models.DateTimeField(default=None, null=True, blank=True)
    created = models.DateTimeField(default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(default=timezone.now, null=True, blank=True)

    # User ip address
    ip_address = models.GenericIPAddressField()

    # Status: pending, accepted, rejected
    status = models.CharField(max_length=1, default=PENDING,
            choices=STATUS_CHOICES, null=False, blank=False)
    status_message = models.TextField(default='', null=True, blank=True)

    class Meta:
        ordering = ['-created']

    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        super(Transaction, self).save(*args, **kwargs)

    def __unicode__(self):
        return 'Transaction(store_id=%s, order_id=%s, order_value=%s, currency=%s)' % (self.store_id, self.order_id, self.order_value, self.currency)
