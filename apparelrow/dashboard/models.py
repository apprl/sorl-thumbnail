import datetime
import decimal

from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import get_language, ugettext_lazy as _
from django.contrib.auth import get_user_model
from jsonfield import JSONField
from django.utils.functional import cached_property
from django.core.mail import mail_admins

from apparelrow.apparel.models import Product
from apparelrow.apparel.utils import currency_exchange
from apparelrow.apparel.base_62_converter import dehydrate
from apparelrow.profile.models import User

import logging

logger = logging.getLogger( __name__ )
MAX_NETWORK_LEVELS = 10


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
    PRODUCT_ADDED = '0'
    PRODUCT_DECLINED = '1'
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

    COST_PER_ORDER = '0'
    COST_PER_CLICK = '1'
    SALE_TYPES_CHOICES = (
        (COST_PER_ORDER, 'Cost per order'),
        (COST_PER_CLICK, 'Cost per click'),
    )

    original_sale_id = models.CharField(max_length=100)
    affiliate = models.CharField(max_length=100)
    vendor = models.ForeignKey('apparel.Vendor', null=True, blank=True, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(null=True, blank=True, default=None)

    user_id = models.PositiveIntegerField(null=True, blank=True)
    product_id = models.PositiveIntegerField(null=True, blank=True)
    placement = models.CharField(max_length=32, null=True, blank=True)

    status = models.CharField(max_length=1, default=INCOMPLETE, choices=STATUS_CHOICES, db_index=True)
    paid = models.CharField(max_length=1, default=PAID_PENDING, choices=PAID_STATUS_CHOICES)
    type = models.CharField(max_length=1, default=COST_PER_ORDER, choices=SALE_TYPES_CHOICES)

    adjusted = models.BooleanField(default=False)
    adjusted_date = models.DateTimeField(default=None, null=True, blank=True)

    cut = models.DecimalField(default='1.0', max_digits=10, decimal_places=3)
    exchange_rate = models.DecimalField(default='1', max_digits=10, decimal_places=6)
    converted_amount = models.DecimalField(default='0.0', max_digits=10, decimal_places=2, help_text=_('Converted sale amount'))
    converted_commission = models.DecimalField(default='0.0', max_digits=10, decimal_places=2, help_text=_('Converted sale commission'))
    amount = models.DecimalField(default='0.0', max_digits=10, decimal_places=2, help_text=_('Sale amount'))
    commission = models.DecimalField(default='0.0', max_digits=10, decimal_places=2, help_text=_('Sale commission'))
    currency = models.CharField(default='EUR', max_length=3, help_text=_('Currency as three-letter ISO code'))
    original_amount = models.DecimalField(default='0.0', max_digits=10, decimal_places=2, help_text=_('Original sale amount'))
    original_commission = models.DecimalField(default='0.0', max_digits=10, decimal_places=2, help_text=_('Original sale commission'))
    original_currency = models.CharField(default='EUR', max_length=3, help_text=_('Original currency as three-letter ISO code'))

    # referral sale
    is_referral_sale = models.BooleanField(default=False)
    referral_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)

    is_promo = models.BooleanField(default=False)

    sale_date = models.DateTimeField(_('Time of sale'), default=timezone.now, null=True, blank=True)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(_('Time modified'), default=timezone.now, null=True, blank=True)
    log_info = JSONField(_('Log info'), null=True, blank=True,
                 help_text='Includes information about the products contained in the sale and their status.')
    source_link = models.CharField(max_length=512, null=True, blank=True)

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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    details = models.ForeignKey('profile.PaymentDetail', on_delete=models.CASCADE)
    amount = models.DecimalField(default='0.0', max_digits=10, decimal_places=2, help_text=_('Sale amount'))
    currency = models.CharField(default='EUR', max_length=3, help_text=_('Currency as three-letter ISO code'))
    paid = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)
    modified = models.DateTimeField(_('Time modified'), default=timezone.now, null=True, blank=True)
    earnings = models.CharField(max_length=1000, null=True, blank=True)

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
    is_subscriber = models.BooleanField(default=False)
    has_cpc_all_stores = models.BooleanField(default=False,
                                             help_text='If checked, all publishers that belong to the Commission Group '
                                                       'will earn per click for all Stores. Next step is to set '
                                                       'cpc_amount and cpc_currency for Cuts for every vendor, and cut '
                                                       'percentage must be 0 to avoid double earnings.')


    class Meta:
        verbose_name = 'Commission Group'

    def __unicode__(self):
        return u'%s' % (self.name,)


class Cut(models.Model):
    group = models.ForeignKey('dashboard.Group', on_delete=models.PROTECT, related_name='cuts')
    vendor = models.ForeignKey('apparel.Vendor', on_delete=models.CASCADE)
    cut = models.DecimalField(default=str(settings.APPAREL_DASHBOARD_CUT_DEFAULT), max_digits=10, decimal_places=3,
                              help_text='Between 1 and 0, default %s. Determines the percentage that goes to the '
                                        'Publisher (and possible Publisher Network owner, if applies). Make sure this '
                                        'value is 0 if Commission Groups that earn per click for all stores and vendor '
                                        'pays per click.' % (settings.APPAREL_DASHBOARD_CUT_DEFAULT,))
    referral_cut = models.DecimalField(default=str(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT), max_digits=10,
                                       decimal_places=3,
                                       help_text='Between 1 and 0, default %s. Determines the percentage that goes to '
                                                 'the referral partner parent.'
                                                 % (settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT,))
    cpc_amount = models.DecimalField(default='0.0', max_digits=10, decimal_places=2,
                                     help_text=_('Pay per click amount only for those publishers that earn per click '
                                                 'for all stores. Set this amount if all publishers in Commission Group'
                                                 'earn per click for ALL stores.'))
    cpc_currency = models.CharField(default='EUR', max_length=3, help_text=_('Pay per click currency only for those '
                                                                             'publishers that earn per click for all '
                                                                             'stores'))
    rules_exceptions = JSONField(null=True, blank=True,
                                 help_text='Creates exceptions for Cuts using the following format: [{"sid": 1, "cut": '
                                           '0.90, "tribute":0.50, "click_cost":"10 SEK"}, {"sid": 2, "cut": 0.90, "tribute":0.5}] where "sid" '
                                           'is the User id. Cut replaces the cut value for the user and the current cut'
                                           ' and Tribute replaces the tribute value the user has to pay to the network '
                                           'owner')

    class Meta:
        ordering = ('group', 'vendor')

    def _calculate_exchange_price(self):
        """
        Return price and currency based on the selected currency. If no
        currency is selected currency language is converted to a currency if
        possible else APPAREL_BASE_CURRENCY is used.
        """
        if not hasattr(self, '_calculated_locale_cost'):
            to_currency = settings.LANGUAGE_TO_CURRENCY.get(get_language(), settings.APPAREL_BASE_CURRENCY)
            rate = currency_exchange(to_currency, self.cpc_currency)
            self._calculated_locale_cost = (rate * self.cpc_amount, to_currency)

        return self._calculated_locale_cost

    @cached_property
    def locale_cpc_amount(self):
        cpc_amount, _ = self._calculate_exchange_price()
        return cpc_amount

    @cached_property
    def locale_cpc_currency(self):
        _, cpc_currency = self._calculate_exchange_price()
        return cpc_currency

    def __unicode__(self):
        return u'%s - %s: %s (%s)' % (self.group, self.vendor, self.cut, self.referral_cut)


class ClickCost(models.Model):
    vendor = models.ForeignKey('apparel.Vendor', on_delete=models.CASCADE)
    amount = models.DecimalField(default='0.0', max_digits=10, decimal_places=2, help_text=_('Click cost'))
    currency = models.CharField(default='EUR', max_length=3, help_text=_('Currency as three-letter ISO code'))

    def _calculate_exchange_price(self):
        """
        Return price and currency based on the selected currency. If no
        currency is selected currency language is converted to a currency if
        possible else APPAREL_BASE_CURRENCY is used.
        """
        if not hasattr(self, '_calculated_locale_cost'):
            to_currency = settings.LANGUAGE_TO_CURRENCY.get(get_language(), settings.APPAREL_BASE_CURRENCY)
            rate = currency_exchange(to_currency, self.currency)

            self._calculated_locale_cost = (rate * self.amount, to_currency)

        return self._calculated_locale_cost

    @cached_property
    def locale_price(self):
        price, _ = self._calculate_exchange_price()
        return price

    @cached_property
    def locale_currency(self):
        _, currency = self._calculate_exchange_price()
        return currency


class Signup(models.Model):
    name = models.CharField(_('Your name'), max_length=255)
    email = models.CharField(_('E-mail'), max_length=255)
    blog = models.CharField(_('Blog URL'), max_length=255)
    store = models.BooleanField(default=False)
    referral_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    created = models.DateTimeField(_('Time created'), default=timezone.now, null=True, blank=True)
    traffic = models.CharField(_('Site traffic'), max_length=100, null=True, blank=True,
                               help_text=_('Unique visitors / month'))

    def __unicode__(self):
        return '%s' % (self.name,)


class StoreCommission(models.Model):
    vendor = models.ForeignKey('apparel.Vendor')
    commission = models.CharField(max_length=255,
                                  help_text=_('Written like X/Y/Z which translates into X-Y%% (Sale Z%%). '
                                              'If the number is 0 then it will not be used. '
                                              'If the said format X/Y/Z is not used at all just the plain text will be displayed. '
                                              'It could be written as 0 if it is a PPC (Pay per click) store.'))
    link = models.CharField(max_length=255, null=True, blank=True, help_text=_('Only our own store links works, should be copied excactly as they appear in short store link admin list without a user id.'))

    def get_standard_from(self, commission, *args):
        """
        Returns (lowest) commission the Store can provide
        """
        normal_cut = args[1]
        publisher_cut = args[3]
        commission_array = commission.split("/")
        standard_from = (decimal.Decimal(commission_array[0].replace("%", ""))*normal_cut*publisher_cut).quantize(decimal.Decimal('1'),rounding=decimal.ROUND_HALF_UP)
        return standard_from

    def calculated_commissions(self, commission, *args):
        from decimal import Decimal, ROUND_HALF_UP
        commission_array = commission.split("/")
        normal_cut = args[1]
        publisher_cut = args[3]

        try:
            if not len(commission_array) == 3 or commission_array[0] == '0':
                logger.warn('Store commission %s is invalidly structured. '
                            'Needs to be in the format [X/Y/Z] where X <> 0!' % self.vendor)
            else:
                standard_from = (Decimal(commission_array[0])*normal_cut*publisher_cut).\
                    quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                standard_to = (Decimal(commission_array[1])*normal_cut*publisher_cut).\
                    quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                sale = (Decimal(commission_array[2])*normal_cut*publisher_cut).\
                    quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                if standard_from == standard_to:
                    commission_array[1] = '0'

                if commission_array[1] == '0':
                    if commission_array[2] == '0':
                        self.commission = _('%(standard_from)s%%' % {'standard_from': standard_from})
                    else:
                        self.commission = _('%(standard_from)s%% (sale items %(sale)s%%)' %
                                            {'standard_from': standard_from, 'sale': sale})
                elif commission_array[2] == '0':
                        self.commission = _('%(standard_from)s-%(standard_to)s%%' %
                                            {'standard_from': standard_from,
                                             'standard_to': standard_to})
                else:
                    self.commission = _('%(standard_from)s-%(standard_to)s%% (sale items %(sale)s%%)' %
                                           {'standard_from': standard_from,
                                            'standard_to': standard_to,
                                            'sale': sale})
        except Exception,msg:
            logger.warn('Unable to convert store commissions for %s. [%s]' % (self,msg))
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

AGGREGATED_DATA_TYPES = (
    ('aggregated_from_total', 'Total Aggregation'),
    ('aggregated_from_product', 'Aggregated From Product'),
    ('aggregated_from_publisher', 'Aggregated From Publisher'),
    ('simple_earning', 'Simple User Earning'),
)


class AggregatedData(models.Model):
    created = models.DateTimeField(default=timezone.now)
    user_id = models.PositiveIntegerField(default=0, db_index=True)
    user_name = models.CharField(max_length=100)
    user_username = models.CharField(max_length=100)
    user_link = models.CharField(max_length=200)
    user_image = models.CharField(max_length=200)

    sale_earnings = models.DecimalField(default=decimal.Decimal(0), max_digits=10, decimal_places=2)
    click_earnings = models.DecimalField(default=decimal.Decimal(0), max_digits=10, decimal_places=2)
    referral_earnings = models.DecimalField(default=decimal.Decimal(0), max_digits=10, decimal_places=2)
    network_sale_earnings = models.DecimalField(default=decimal.Decimal(0), max_digits=10, decimal_places=2)
    network_click_earnings = models.DecimalField(default=decimal.Decimal(0), max_digits=10, decimal_places=2)
    sale_plus_click_earnings = models.DecimalField(default=decimal.Decimal(0), max_digits=10, decimal_places=2)
    total_network_earnings = models.DecimalField(default=decimal.Decimal(0), max_digits=10, decimal_places=2)

    sales = models.PositiveIntegerField(default=0)
    network_sales = models.PositiveIntegerField(default=0)
    referral_sales = models.PositiveIntegerField(default=0)
    paid_clicks = models.PositiveIntegerField(default=0)
    total_clicks = models.PositiveIntegerField(default=0)

    data_type = models.CharField(max_length=100, choices=AGGREGATED_DATA_TYPES)

    aggregated_from_id = models.PositiveIntegerField(default=0)
    aggregated_from_name = models.CharField(max_length=100)
    aggregated_from_slug = models.CharField(max_length=100)
    aggregated_from_link = models.CharField(max_length=200)
    aggregated_from_image = models.CharField(max_length=200)

USER_EARNING_TYPES = (
    ('apprl_commission', 'APPRL Earnings'),
    ('referral_sale_commission', 'Referral Sale Earnings'),
    ('referral_signup_commission', 'Referral Signup Earnings'),
    ('publisher_sale_commission', 'Publisher Sale Earnings'),
    ('publisher_network_tribute', 'Network Earnings'),

    ('publisher_network_click_tribute', 'Network Earnings per Clicks'),
    ('publisher_sale_click_commission', 'Earnings per Clicks'),

    ('publisher_network_click_tribute_all_stores', 'Network Earnings per Clicks'),
    ('publisher_sale_click_commission_all_stores', 'Earnings per Clicks'),
)

@receiver(pre_save, sender=AggregatedData, dispatch_uid='aggregated_data_pre_save')
def aggregated_data_pre_save(sender, instance, *args, **kwargs):
    """
    Trim the string if its larger than 100 chars.
    :param sender:
    :param instance:
    :param args:
    :param kwargs:
    :return:
    """
    #if instance.aggregated_from_name:
    if instance.aggregated_from_name:
        instance.aggregated_from_name = instance.aggregated_from_name[:99]
    else:
        instance.aggregated_from_name = ""

    if instance.aggregated_from_slug:
        instance.aggregated_from_slug = instance.aggregated_from_slug[:99]
    else:
        instance.aggregated_from_slug = ""

    if instance.aggregated_from_link:
        instance.aggregated_from_link = instance.aggregated_from_link[:199]
    else:
        instance.aggregated_from_link = ""

    if instance.aggregated_from_image:
        instance.aggregated_from_image = instance.aggregated_from_image[:199]
    else:
        instance.aggregated_from_image = ""

class UserEarning(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='earning_user', null=True, on_delete=models.PROTECT)
    user_earning_type = models.CharField(max_length=100, choices=USER_EARNING_TYPES)
    sale = models.ForeignKey('dashboard.Sale', null=True, blank=True, on_delete=models.PROTECT)
    from_product = models.ForeignKey('apparel.Product', null=True, blank=True, on_delete=models.PROTECT)
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    amount = models.DecimalField(default='0.0', max_digits=10, decimal_places=2)
    date = models.DateTimeField(_('Created'), default=timezone.now, null=True, blank=True)
    status = models.CharField(max_length=1, default=Sale.INCOMPLETE, choices=Sale.STATUS_CHOICES, db_index=True)
    paid = models.CharField(max_length=1, default=Sale.PAID_PENDING, choices=Sale.PAID_STATUS_CHOICES)

@receiver(post_save, sender=Sale, dispatch_uid='sale_post_save')
def sale_post_save(sender, instance, created, **kwargs):
    """
    sale_post_save is triggered after a Sale has been created or updated. It creates the respective earnings for this
    sale.
    """
    logger.info("Sale with id %s saved with user id %s and type %s" % (instance.id, instance.user_id, instance.type))
    with transaction.atomic():
        if created:
            # If sale is created, create the respectives earnings
            create_earnings(instance)
        else:
            # Update if UserEarning instances for the respective sale exists, otherwise create them
            if UserEarning.objects.filter(sale=instance).exists():
                # Update earnings if sale has been updated.
                earnings = UserEarning.objects.filter(sale=instance)
                if instance.status >= Sale.CONFIRMED:
                    for earning in earnings:
                        earning.status = instance.status
                        earning.save()
                else:
                    # Remove earnings if sale has been removed.
                    UserEarning.objects.filter(sale=instance).delete()
                    create_earnings(instance)
                str_date = instance.sale_date.strftime('%Y-%m-%d')

                # Add date from updated sale/earnings to a quere, so the associated aggregated data will be
                # updated/generated later as well. (update_aggregated_data job)
                update_list = cache.get(settings.APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA)
                if update_list:
                    if str_date not in update_list:
                        update_list = "%s,%s" % (update_list, str_date)
                        cache.set(settings.APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA, update_list)
                else:
                    cache.set(settings.APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA, str_date)
            else:
                create_earnings(instance)

def create_earnings(instance):
    """
    Identify and handles when the sale is a Referral Signup Bonus or when it's another type of sale.
    """
    if not instance.is_promo:
        create_user_earnings(instance)
        if instance.is_referral_sale:
            create_referral_earning(instance)
    else:
        user = User.objects.get(id=instance.user_id)
        UserEarning.objects.\
            create(user=user, user_earning_type='referral_signup_commission', sale=instance,
                   amount=settings.APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION, date=instance.sale_date,
                   status=instance.status)
        mail_admins('Referral Signup bonus created',
                    'A referral Signup bonus has been created for user %s (%s)' % (user.display_name, user.id))

def create_referral_earning(sale):
    """
    Create referral earnings when the sale is a referral sale.
    User associated to the sale must exist and have a Cut instance (referral_cut) associated to the Vendor
    """
    total_commission = sale.converted_commission
    referral_user = sale.referral_user
    user = User.objects.get(id=sale.user_id)
    commission_group = referral_user.partner_group
    product = None

    sale_product = Product.objects.filter(id=sale.product_id)

    if not len(sale_product) == 0:
        product = sale_product[0]

    if commission_group:
        commission_group_cut = Cut.objects.get(group=commission_group, vendor=sale.vendor)
        referral_cut = commission_group_cut.referral_cut
        if referral_cut:
            referral_commission = total_commission * referral_cut
            UserEarning.objects.create(user=referral_user,
                                                                 user_earning_type='referral_sale_commission',
                                                                 sale=sale, from_product=product, from_user=user,
                                                                 amount=referral_commission, date=sale.sale_date,
                                                                 status=sale.status)
        else:
            logger.warning('Cut matching query does not exist %s - %s' % (commission_group, sale.vendor))
    else:
        logger.warning('User %s should have assigned a comission group'%user)

def create_user_earnings(sale):
    """
    Create user earnings associated excluding referral sales. More specifically, those earnings types are apprl
    commissions, publisher sale and click commissions, and publisher network owner sale and click commissions.

    If user_id is not 0 (id reserved only for APPRL), the User must exists in order to proceed. Also, the user must
    have a Cut associated,
    """
    total_commission = sale.converted_commission
    product = None
    is_general_click_earning = False

    sale_product = Product.objects.filter(id=sale.product_id)
    if not len(sale_product) == 0:
        product = sale_product[0]

    earning_type = 'publisher_sale_commission' if sale.type == Sale.COST_PER_ORDER \
        else 'publisher_sale_click_commission'

    if sale.user_id:
        try:
            user = User.objects.get(id=sale.user_id)
        except User.DoesNotExist:
            logger.warning('Sale %s is connected to a User %s that does not exist.' % (sale.id,sale.user_id))
            return

        commission_group = user.partner_group

        if commission_group:
            try:
                commission_group_cut = Cut.objects.get(group=commission_group, vendor=sale.vendor)
            except Cut.DoesNotExist:
                logger.warning('Cut matching query does not exist %s - %s' % (commission_group, sale.vendor))
                return
            cut = commission_group_cut.cut

            # Handle exceptions for the publisher Cut
            try:
                data_exceptions = commission_group_cut.rules_exceptions
                for data in data_exceptions:
                    if data['sid'] == user.id:
                        cut = decimal.Decimal(data['cut'])
            except:
                logger.info("No exceptions for cuts defined for commission group %s and store %s"%(commission_group,
                                                                                                    sale.vendor))
            # If the earning is for a publisher that earns per click for all stores, the publisher (and the publisher
            # network owner, if applies) will get 100% of this earning
            if sale.affiliate == "cpc_all_stores":
                cut = 1
                earning_type = "publisher_sale_click_commission_all_stores"
                is_general_click_earning = True

            if cut is not None:
                try:
                    publisher_commission = total_commission * cut
                    apprl_commission = total_commission - publisher_commission

                    # Create earning(s) for the publisher network owner(s)
                    if user.owner_network and not user.owner_network.id == user.id:
                        publisher_commission = create_earnings_publisher_network(user, publisher_commission, sale,
                                                                                 product,MAX_NETWORK_LEVELS,
                                                                                 is_general_click_earning)

                    # Create apprl commission
                    UserEarning.objects.create(user_earning_type='apprl_commission', sale=sale,
                                                                         from_product=product, from_user=user,
                                                                         amount=apprl_commission, date=sale.sale_date,
                                                                         status=sale.status)

                    # Create user earning for the publisher associated to the sale
                    UserEarning.objects.create( user=user,
                                                                          user_earning_type=earning_type, sale=sale,
                                                                          from_product=product,
                                                                          amount=publisher_commission,
                                                                          date=sale.sale_date, status=sale.status)
                except:
                    logger.error("Error creating earnings within the publisher network")
            else:
                logger.warning('No Cut related to Commission group %s and Store %s' % (user, sale.vendor))
        else:
            logger.warning('User %s should have assigned a comission group' % user)
    else:
        # Sale was generated from APPRL.com, so in this case only an earning for APPRL is created
        UserEarning.objects.create(user_earning_type='apprl_commission', sale=sale,
                                                                     from_product=product, amount=total_commission,
                                                                     date=sale.sale_date, status=sale.status)

def create_earnings_publisher_network(user, publisher_commission, sale, product, counter, cpc_all_stores=False):
    """
    Recursive method that creates user earnings for the publisher network owner(s), which means the publisher network
    could have more than one level in hierarchy.

    Owner must exist, and owner user must differ of publisher user. Also it has a counter to avoid infinite loops. It
    takes into consideration Cuts exceptions, if owner belongs to a commission group and there is an exception.
    """
    owner = user.owner_network
    counter -= 1
    if owner and not user.id == owner.id and not counter == 0:
        owner_tribute = owner.owner_network_cut
        if owner_tribute > 1 or owner_tribute < 0:
            logger.warning('Owner network cut must be a value between 0 and 1 for user %s'%(owner))
            raise
        commission_group_user = user.partner_group

        if commission_group_user:
            try:
                commission_group_cut = Cut.objects.get(group=commission_group_user, vendor=sale.vendor)
            except Cut.DoesNotExist:
                logger.warning('Cut matching query does not exist %s - %s' % (commission_group_user, sale.vendor))
                return

            # Handle exceptions for owner cuts
            try:
                data_exceptions = commission_group_cut.rules_exceptions
                for data in data_exceptions:
                    if data['sid'] == user.id:
                        owner_tribute = decimal.Decimal(data['tribute'])
            except:
                pass

        # Calculate owner earning
        owner_earning = publisher_commission * owner_tribute
        publisher_commission -= owner_earning

        if owner.owner_network:
            owner_earning = create_earnings_publisher_network(owner, owner_earning, sale, product, counter,
                                                              cpc_all_stores)

        earning_type = 'publisher_network_tribute' if sale.type == Sale.COST_PER_ORDER\
            else 'publisher_network_click_tribute'
        if cpc_all_stores:
            earning_type = "publisher_network_click_tribute_all_stores"

        UserEarning.objects.create( user=owner, user_earning_type=earning_type, sale=sale,
                                                              from_product=product, from_user=user, amount=owner_earning,
                                                              date=sale.sale_date, status=sale.status)
    return publisher_commission
