import datetime

from django.conf import settings
from django.db import models
from django.db.models import get_model
from django.db.models.signals import pre_save, post_save
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

    class Meta:
        verbose_name = 'Commission Group'

    def __unicode__(self):
        return u'%s' % (self.name,)


class Cut(models.Model):
    group = models.ForeignKey('dashboard.Group', null=False, blank=False, on_delete=models.PROTECT, related_name='cuts')
    vendor = models.ForeignKey('apparel.Vendor', null=False, blank=False, on_delete=models.CASCADE)
    cut = models.DecimalField(null=False, blank=False, default=str(settings.APPAREL_DASHBOARD_CUT_DEFAULT), max_digits=10, decimal_places=3,
                              help_text='Between 1 and 0, default %s. Determines the percentage that goes to the Publisher (and possible Publisher Network owner, if applies)' % (settings.APPAREL_DASHBOARD_CUT_DEFAULT,))
    referral_cut = models.DecimalField(null=False, blank=False, default=str(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT), max_digits=10, decimal_places=3,
                                       help_text='Between 1 and 0, default %s. Determines the percentage that goes to the referral partner parent.' % (settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT,))

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

        sale, created = Sale.objects.get_or_create(original_sale_id=data['original_sale_id'], defaults=data)

USER_EARNING_TYPES = (
    ('apprl_commission', 'APPRL Commission'),
    ('referral_sale_commission', 'Referral Sale Commission'),
    ('referral_signup_commission', 'Referral Signup Commission'),
    ('publisher_sale_commission', 'Publisher Sale Commission'),
    ('publisher_network_tribute', 'Network Commission'),
)

class UserEarning(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='earning_user', null=True, blank=False, on_delete=models.PROTECT)
    user_earning_type = models.CharField(max_length=100, null=False, blank=False, choices=USER_EARNING_TYPES)
    sale = models.ForeignKey('dashboard.Sale', null=True, blank=True, on_delete=models.PROTECT)
    from_product = models.ForeignKey('apparel.Product', null=True, blank=True, on_delete=models.PROTECT)
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=False, on_delete=models.PROTECT)
    amount = models.DecimalField(null=False, blank=False, default='0.0', max_digits=10, decimal_places=2)
    date = models.DateTimeField(_('Payout Date'), default=timezone.now, null=True, blank=True)
    status = models.CharField(max_length=1, default=Sale.INCOMPLETE, choices=Sale.STATUS_CHOICES, null=False, blank=False, db_index=True)
    paid = models.CharField(max_length=1, default=Sale.PAID_PENDING, choices=Sale.PAID_STATUS_CHOICES, null=False, blank=False)

@receiver(post_save, sender=Sale, dispatch_uid='sale_post_save')
def sale_post_save(sender, instance, created, **kwargs):
    if created:
        create_earnings(instance)
    else:
        earnings = get_model('dashboard', 'UserEarning').objects.filter(sale=instance)
        if len(earnings) == 0:
            create_earnings(instance)
        else:
            for earning in earnings:
                earning.status = instance.status
                earning.save()

def create_earnings(instance):
    if not instance.is_promo:
        create_user_earnings(instance)
        if instance.is_referral_sale:
            create_referral_earning(instance)
    else:
        user = get_model('profile', 'User').objects.get(id=instance.user_id)
        get_model('dashboard', 'UserEarning').objects.create(user=user, user_earning_type='referral_signup_commission',
            sale=instance, amount=settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION, date=instance.sale_date, status=instance.status)

def create_referral_earning(sale):
    total_commission = sale.original_commission
    referral_user = sale.referral_user
    user = get_model('profile', 'User').objects.get(id=sale.user_id)
    commission_group = referral_user.partner_group
    product = None

    sale_product = get_model('apparel', 'Product').objects.filter(id=sale.product_id)

    if not len(sale_product) == 0:
        product = sale_product(0)

    if commission_group:
        commission_group_cut = Cut.objects.get(group=commission_group, vendor=sale.vendor)
        referral_cut = commission_group_cut.referral_cut
        if referral_cut:
            referral_commission = total_commission * referral_cut
            get_model('dashboard', 'UserEarning').objects.create(user=referral_user,
                                                                 user_earning_type='referral_sale_commission',
                                                                 sale=sale, from_product=product, from_user=user,
                                                                 amount=referral_commission, date=sale.sale_date,
                                                                 status=sale.status)
        else:
            logging.warning('No Cut related to Commission group %s and Store %s'%(user, sale.vendor))
    else:
        logging.warning('User %s should have assigned a comission group'%user)

def create_user_earnings(sale):
    total_commission = sale.original_commission
    product = None

    user = get_model('profile', 'User').objects.get(id=sale.user_id)
    sale_product = get_model('apparel', 'Product').objects.filter(id=sale.product_id)
    commission_group = user.partner_group

    if not len(sale_product) == 0:
        product = sale_product(0)

    if commission_group:
        commission_group_cut = Cut.objects.get(group=commission_group, vendor=sale.vendor)
        cut = commission_group_cut.cut

        if cut:
            publisher_commission = total_commission * cut
            apprl_commission = total_commission - publisher_commission

            get_model('dashboard', 'UserEarning').objects.create(user_earning_type='apprl_commission', sale=sale,
                                                                 from_product=product, from_user=user,
                                                                 amount=apprl_commission, date=sale.sale_date,
                                                                 status=sale.status)

            if user.owner_network:
                publisher_commission = create_earnings_publisher_network(user, publisher_commission, sale, product)

            get_model('dashboard', 'UserEarning').objects.create( user=user,
                                                                  user_earning_type='publisher_sale_commission',
                                                                  sale=sale, from_product=product,
                                                                  amount=publisher_commission, date=sale.sale_date,
                                                                  status=sale.status)

        else:
            logging.warning('No Cut related to Commission group %s and Store %s'%(user, sale.vendor))
    else:
        logging.warning('User %s should have assigned a comission group'%user)

def create_earnings_publisher_network(user, publisher_commission, sale, product):
    owner = user.owner_network
    owner_tribute = owner.owner_network_cut
    if owner_tribute > 1:
        owner_tribute = 1
        logging.warning('Owner network cut must be a value between 0 and 1')
    owner_earning = publisher_commission * owner_tribute
    publisher_commission -= owner_earning

    if owner.owner_network:
        owner_earning = create_earnings_publisher_network(owner, owner_earning, sale, product)

    get_model('dashboard', 'UserEarning').objects.create( user=owner, user_earning_type='publisher_network_tribute',
                                                          sale=sale, from_product=product, from_user=user,
                                                          amount=owner_earning, date=sale.sale_date, status=sale.status)
    return publisher_commission