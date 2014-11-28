import datetime

from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model

from apparelrow.apparel.base_62_converter import dehydrate
import logging

log = logging.getLogger( __name__ )

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
    quantity = models.PositiveIntegerField(null=True, blank=True, default=None)

    user_id = models.PositiveIntegerField(null=True, blank=True)
    product_id = models.PositiveIntegerField(null=True, blank=True)
    placement = models.CharField(max_length=32, null=True, blank=True)

    status = models.CharField(max_length=1, default=INCOMPLETE, choices=STATUS_CHOICES, null=False, blank=False, db_index=True)
    paid = models.CharField(max_length=1, default=PAID_PENDING, choices=PAID_STATUS_CHOICES, null=False, blank=False)
    adjusted = models.BooleanField(null=False, blank=False, default=False)
    adjusted_date = models.DateTimeField(default=None, null=True, blank=True)

    cut = models.DecimalField(null=False, blank=False, default='1.0', max_digits=10, decimal_places=3)
    exchange_rate = models.DecimalField(null=False, blank=False, default='1', max_digits=10, decimal_places=6)
    converted_amount = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Converted sale amount'))
    converted_commission = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Converted sale commission'))
    amount = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Sale amount'))
    commission = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Sale commission'))
    currency = models.CharField(null=False, blank=False, default='EUR', max_length=3, help_text=_('Currency as three-letter ISO code'))
    original_amount = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Original sale amount'))
    original_commission = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Original sale commission'))
    original_currency = models.CharField(null=False, blank=False, default='EUR', max_length=3, help_text=_('Original currency as three-letter ISO code'))

    # referral sale
    is_referral_sale = models.BooleanField(default=False, null=False, blank=False)
    referral_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)

    is_promo = models.BooleanField(default=False, null=False, blank=False)

    sale_date = models.DateTimeField(_('Time of sale'), default=timezone.now, null=True, blank=True)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(_('Time modified'), default=timezone.now, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        super(Sale, self).save(*args, **kwargs)

    def __unicode__(self):
        vendor_name = 'None'
        if self.vendor:
            vendor_name = self.vendor.name

        return u'%s - %s: %s %s %s' % (self.affiliate, vendor_name, self.commission, self.currency, self.status)

    class Meta:
        ordering = ['-sale_date']

class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=False, blank=False, on_delete=models.CASCADE)
    details = models.ForeignKey('profile.PaymentDetail', null=False, blank=False, on_delete=models.CASCADE)
    amount = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2, help_text=_('Sale amount'))
    currency = models.CharField(null=False, blank=False, default='EUR', max_length=3, help_text=_('Currency as three-letter ISO code'))
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
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name='owner_group', help_text='Assign a group owner if publishers of this group will belong to an owner, for example a blog network.')
    owner_cut = models.DecimalField(null=True, blank=True, default='1.00', max_digits=10, decimal_places=3,
                                    help_text='Between 0 and 2, how big % of the blogger\'s earned commission should go to the network. (1 equals 100%, which is the same amount going to the blogger goes to the network)')
    is_subscriber = models.BooleanField(default=False, null=False, blank=False)

    def __unicode__(self):
        return u'%s' % (self.name,)


class Cut(models.Model):
    group = models.ForeignKey('dashboard.Group', null=False, blank=False, on_delete=models.PROTECT, related_name='cuts')
    vendor = models.ForeignKey('apparel.Vendor', null=False, blank=False, on_delete=models.CASCADE)
    cut = models.DecimalField(null=False, blank=False, default=str(settings.APPAREL_DASHBOARD_CUT_DEFAULT), max_digits=10, decimal_places=3,
                              help_text='Between 1 and 0, default %s' % (settings.APPAREL_DASHBOARD_CUT_DEFAULT,))
    referral_cut = models.DecimalField(null=False, blank=False, default=str(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT), max_digits=10, decimal_places=3,
                                       help_text='Between 1 and 0, default %s' % (settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT,))

    def __unicode__(self):
        return u'%s - %s: %s (%s)' % (self.group, self.vendor, self.cut, self.referral_cut)


class Signup(models.Model):
    name = models.CharField(_('Your name'), max_length=255)
    email = models.CharField(_('E-mail'), max_length=255)
    blog = models.CharField(_('Blog URL'), max_length=255)
    store = models.BooleanField(default=False)
    referral_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)

    def __unicode__(self):
        return '%s' % (self.name,)


class StoreCommission(models.Model):
    vendor = models.ForeignKey('apparel.Vendor', null=False, blank=False)
    commission = models.CharField(max_length=255,help_text=_('Written like X/Y/Z which translates into X-Y%% (Sale Z%%). If the number is 0 then it will not be used. '
                                                             'If the said format X/Y/Z is not used at all just the plain text will be displayed.'))
    link = models.CharField(max_length=255, null=True, blank=True, help_text=_('Only our own store links works, should be copied excactly as they appear in short store link admin list without a user id.'))


    def calculated_commissions(self,commission,*args):
        from decimal import Decimal,ROUND_HALF_UP,ROUND_UP
        commission_array = commission.split("/")
        normal_cut = args[1]
        referral_cut = args[2]

        try:
            if not len(commission_array) == 3 or commission_array[0] == '0':
                log.warn('Store commission %s is invalidly structured. Needs to be in the format [X/Y/Z] where X <> 0!' % self.vendor)
            else:
                standard_from = (Decimal(commission_array[0])*normal_cut).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
                standard_to = (Decimal(commission_array[1])*normal_cut).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
                sale = (Decimal(commission_array[2])*normal_cut).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
                if standard_from == standard_to:
                    commission_array[1] = '0'

                if commission_array[1] == '0':
                    if commission_array[2] == '0':
                        self.commission =  _('%(standard_from)s%%' % {'standard_from':standard_from})
                    else:
                        self.commission =  _('%(standard_from)s%% (Sale %(sale)s%%)' % {'standard_from':standard_from,
                                                                                    'sale':sale})
                elif commission_array[2] == '0':
                        self.commission = _('%(standard_from)s-%(standard_to)s%%' %
                                            {'standard_from':standard_from,
                                             'standard_to':standard_to})
                else:
                    self.commission = _('%(standard_from)s-%(standard_to)s%% (Sale %(sale)s%%)' %
                                           {'standard_from':standard_from,
                                            'standard_to':standard_to,
                                            'sale':sale})
        except Exception,msg:
            log.warn('Unable to convert store commissions for %s. [%s]' % (self,msg))
        return self
#
# Model signals
#

@receiver(pre_save, sender=get_user_model(), dispatch_uid='pre_save_update_referral_code')
def pre_save_update_referral_code(sender, instance, *args, **kwargs):
    if instance.is_partner and instance.referral_partner and instance.pk:
        instance.referral_partner_code = dehydrate(1000000 + instance.pk)
    else:
        instance.referral_partner = False
        instance.referral_partner_code = None

    if instance.referral_partner_parent and instance.is_partner and not instance.referral_partner_parent_date:
        instance.referral_partner_parent_date = timezone.now() + datetime.timedelta(days=180)

        data = {
            'affiliate': 'referral_promo',
            'original_sale_id': 'referral_promo_%s' % (instance.pk,),
            'user_id': instance.pk,
            'is_referral_sale': False,
            'is_promo': True,
            'exchange_rate': '1',
            'converted_amount': settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION,
            'converted_commission': settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION,
            'amount': settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION,
            'commission': settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION,
            'currency': 'EUR',
            'original_amount': settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION,
            'original_commission': settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION,
            'original_currency': 'EUR',
            'status': Sale.CONFIRMED,
        }

        instance, created = Sale.objects.get_or_create(original_sale_id=data['original_sale_id'], defaults=data)

PAYOUT_TYPES = (
    ('referral_sale_commission', 'Referral Sale Commission'),
    ('referral_signup_commission', 'Referral Signup Commission'),
    ('publisher_sale_commission', 'Publisher Sale Commission'),
    ('publisher_network_commission', 'Publisher Network Commission'),
)

class Payout(models.Model):
    payout_type = models.CharField(max_length=100, null=False, blank=False)
    sale = models.ForeignKey('dashboard.Sale', null=True, blank=True, on_delete=models.PROTECT)
    from_product = models.ForeignKey('apparel.Product', null=True, blank=True, on_delete=models.PROTECT)
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=False, blank=False, on_delete=models.PROTECT)
    amount = models.DecimalField(null=False, blank=False, default='1.0', max_digits=10, decimal_places=3)
    date = models.DateTimeField(_('Payout Date'), default=timezone.now, null=True, blank=True)