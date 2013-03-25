from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class Transaction(models.Model):
    ACCEPTED = 'A'
    REJECTED = 'R'
    PENDING = 'P'
    INVALID = 'I'
    STATUS_CHOICES = (
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
        (PENDING, 'Pending'),
        (INVALID, 'Invalid'),
    )

    company_id = models.CharField(max_length=128)
    order_id = models.CharField(max_length=128)
    order_value = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)
    currency = models.CharField(null=False, blank=False, default='SEK', max_length=3, help_text=_('Currency as three-letter ISO code'))

    created = models.DateTimeField(default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(default=timezone.now, null=True, blank=True)

    # User ip address
    ip_address = models.GenericIPAddressField()

    # Status: pending, accepted, rejected
    status = models.CharField(max_length=1, default=PENDING,
            choices=STATUS_CHOICES, null=False, blank=False)
    status_message = models.TextField(default='')

    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        super(Sale, self).save(*args, **kwargs)
