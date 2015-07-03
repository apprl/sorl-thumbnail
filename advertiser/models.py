import decimal

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property

from advertiser.utils import calculate_balance, get_transactions


class Store(models.Model):
    identifier = models.CharField(max_length=64, null=False, blank=False, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, default=None, blank=True, null=True, on_delete=models.SET_NULL, related_name='advertiser_store')
    balance = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)
    commission_percentage = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)
    cookie_days = models.PositiveIntegerField(null=False, blank=False, default=30)
    vendor = models.ForeignKey('apparel.Vendor', null=False, blank=False, related_name='store')

    class Meta:
        ordering = ('identifier',)

    def __unicode__(self):
        return u'%s' % (self.identifier)

@receiver(post_save, sender=Store, dispatch_uid='store_post_save')
def store_post_save(sender, instance, **kwargs):
    try:
        latest_history = StoreHistory.objects.latest('created')
        if latest_history.balance != instance.balance:
            StoreHistory.objects.create(store=instance, balance=instance.balance)
    except StoreHistory.DoesNotExist as e:
        StoreHistory.objects.create(store=instance, balance=instance.balance)


class StoreHistory(models.Model):
    store = models.ForeignKey('advertiser.Store', null=False, blank=False, on_delete=models.CASCADE, related_name='history')
    balance = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)
    created = models.DateTimeField(default=timezone.now, null=True, blank=True)

    class Meta:
        ordering = ['-created']

    def __unicode__(self):
        return u'StoreHistory(%s, %s)' % (self.balance, self.created)


class StoreInvoice(models.Model):
    store = models.ForeignKey('advertiser.Store', null=False, blank=False,
                              on_delete=models.CASCADE, related_name='invoices')
    created = models.DateTimeField(default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(default=timezone.now, null=True, blank=True)
    is_paid = models.BooleanField(default=False, null=False, blank=False)

    class Meta:
        ordering = ['-created']

    def save(self, *args, **kwargs):
        self.modified = timezone.now()

        super(StoreInvoice, self).save(*args, **kwargs)

    def get_total(self, currency=None):
        total = self.transactions.aggregate(total=models.Sum('commission')).get('total', 0)
        if not total:
            return 0

        return total

@receiver(post_save, sender=StoreInvoice, dispatch_uid='store_invoice_post_save')
def store_invoice_post_save(sender, instance, created, **kwargs):
    if created:
        for transaction in get_transactions(instance.store):
            transaction.invoice = instance
            transaction.save()


class Product(models.Model):
    transaction = models.ForeignKey('advertiser.Transaction', null=False, blank=False, on_delete=models.CASCADE, related_name='products')
    sku = models.CharField(max_length=255, null=False, blank=False)
    price = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(null=False, blank=False, default=0)

    def __unicode__(self):
        return u'Product(%s, %s, %s)' % (self.sku, self.price, self.quantity)


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

    invoice = models.ForeignKey('advertiser.StoreInvoice', null=True, blank=True,
                                on_delete=models.SET_NULL, related_name='transactions')
    store_id = models.CharField(max_length=64, null=False, blank=False, db_index=True)
    order_id = models.CharField(max_length=128, null=False, blank=False)

    currency = models.CharField(null=False, blank=False, default='EUR', max_length=3, help_text=_('Currency as three-letter ISO code'))
    exchange_rate = models.DecimalField(null=False, blank=False, default='1', max_digits=12, decimal_places=6)
    order_value = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)
    commission = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)

    original_currency = models.CharField(null=False, blank=False, default='EUR', max_length=3, help_text=_('Original currency as three-letter ISO code'))
    original_order_value = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)
    original_commission = models.DecimalField(null=False, blank=False, default='0.0', max_digits=12, decimal_places=2)

    cookie_date = models.DateTimeField(default=None, null=True, blank=True)
    created = models.DateTimeField(default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(default=timezone.now, null=True, blank=True)

    # Custom user data
    custom = models.CharField(max_length=128, null=True, blank=True)

    # User ip address
    ip_address = models.GenericIPAddressField()

    # Status: pending, accepted, rejected
    status = models.CharField(max_length=1, default=PENDING,
            choices=STATUS_CHOICES, null=False, blank=False)
    status_message = models.TextField(default='', null=True, blank=True)
    status_date = models.DateTimeField(default=None, null=True, blank=True)

    automatic_accept = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created']

    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        self.currency = self.currency.upper()
        if not self.status_date and (self.status == Transaction.ACCEPTED or self.status == Transaction.REJECTED):
            self.status_date = timezone.now()

        super(Transaction, self).save(*args, **kwargs)

    def accept(self):
        if self.store_id:
            try:
                store = Store.objects.get(identifier=self.store_id)
            except Store.DoesNotExist:
                return

            self.status = Transaction.ACCEPTED
            self.save()

            store.balance -= self.commission
            store.save()

    def __unicode__(self):
        return 'Transaction(%s, %s, order="%s %s", commission="%s %s", status=%s)' % (self.store_id, self.order_id, self.order_value, self.currency, self.commission, self.currency, self.status)

@receiver([post_delete, post_save], sender=Transaction, dispatch_uid='transaction_update')
def transaction_update(sender, instance, **kwargs):
    calculate_balance(instance.store_id)


class Cookie(models.Model):
    cookie_id = models.CharField(max_length=32, null=False, blank=False, db_index=True)
    store_id = models.CharField(max_length=128, null=False, blank=False, db_index=True)

    old_cookie_id = models.CharField(max_length=32, null=True, blank=True)

    # User data
    custom = models.CharField(max_length=32, null=True, blank=True)

    # Date
    created = models.DateTimeField(default=timezone.now, null=False, blank=False)

    class Meta:
        ordering = ['-created']
