import datetime
import decimal
from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.core.urlresolvers import reverse
from django.core import management, mail
from django.conf import settings

@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestProductStat(TestCase):
    fixtures = ['test-statistics.yaml']

    def _login(self):
        normal_user = get_user_model().objects.get(username='normal_user')
        is_logged_in = self.client.login(username='normal_user', password='normal')
        self.assertTrue(is_logged_in)

    def setUp(self):
        group = get_model('dashboard', 'Group').objects.create(name='group_name')

        normal_user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        normal_user.is_partner = True
        normal_user.partner_group = group
        normal_user.save()

        cpc_vendor = get_model('apparel', 'Vendor').objects.get(pk=2)

        get_model('dashboard', 'Cut').objects.create(cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, group=group,
                                                     vendor=cpc_vendor)
        self._login()

    @override_settings(VENDOR_LOCATION_MAPPING={"CPC Vendor":["SE"], "default":["ALL","SE","NO","US"],})
    def test_click_is_not_valid(self):
        """
        Tests that when a click ip does not match the market of the cpc store, the click is not valid
        and it will not be included in earnings
        """
        user = get_user_model().objects.get(username='normal_user')
        product = get_model('apparel', 'Product').objects.get(slug='brand-cpc-product')

        response = self.client.post(reverse('product-track', args=[product.pk, 'Ext-Link', user.pk]), follow=True,
                                    REMOTE_ADDR="190.104.96.3")

        valid_clicks = get_model('statistics', 'ProductStat').objects.filter(is_valid=True).count()
        self.assertEqual(valid_clicks, 0)
        str_date = datetime.date.today().strftime('%Y-%m-%d')
        management.call_command('clicks_summary', date=str_date, verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 0)
        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 0)

    @override_settings(VENDOR_LOCATION_MAPPING={"CPC Vendor":["SE"], "default":["ALL","SE","NO","US"],})
    def test_click_is_valid(self):
        """
        Tests that when a click ip does  match the market of the cpc store, the click is valid and it will be included
        in earnings
        """
        user = get_user_model().objects.get(username='normal_user')
        product = get_model('apparel', 'Product').objects.get(slug='brand-cpc-product')
        clickcost = get_model('dashboard', 'ClickCost').objects.get(pk=1)

        response = self.client.post(reverse('product-track', args=[product.pk, 'Ext-Link', user.pk]), follow=True,
                                    REMOTE_ADDR="2.64.0.2")

        valid_clicks = get_model('statistics', 'ProductStat').objects.filter(is_valid=True).count()
        self.assertEqual(valid_clicks, 1)
        str_date = datetime.date.today().strftime('%Y-%m-%d')
        management.call_command('clicks_summary', date=str_date, verbosity=0, interactive=False)

        # Check if number of Sales and UserEarnings are correct
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 2)

        # Check if earnings amounts are correct
        earning_user = get_model('dashboard', 'UserEarning').objects.get(user=user)
        self.assertEqual(earning_user.amount,
                         clickcost.amount * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

        earning_apprl = get_model('dashboard', 'UserEarning').objects.get(user=None)
        self.assertEqual(earning_apprl.amount, clickcost.amount * (1 - decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT)))

    def test_unique_clicks_per_day(self):
        """
        Tests that only one click could be made to the same product from the same browser, once a day
        """
        user = get_user_model().objects.get(username='normal_user')
        product = get_model('apparel', 'Product').objects.get(slug='brand-product')
        other_product = get_model('apparel', 'Product').objects.get(slug='brand-other-product')
        response = self.client.post(reverse('product-track', args=[product.pk, 'Ext-Link', user.pk]), follow=True)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.count(), 1)

        # Doing the same request shouldn't created another click
        response = self.client.post(reverse('product-track', args=[product.pk, 'Ext-Link', user.pk]), follow=True)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.count(), 1)

        # Click other product should generate a new click
        response = self.client.post(reverse('product-track', args=[other_product.pk, 'Ext-Link', user.pk]), follow=True)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.count(), 2)

    def test_clicks_limit_per_vendor_not_exceeded_custom_value(self):
        """
        Test an email is not sent to the admins when a limit is not exceeded
        """
        ip = "192.128.2.3"
        vendor = get_model('apparel', 'Vendor').objects.get(pk=2)
        product = get_model('apparel', 'Product').objects.get(slug='brand-cpc-product')
        user = get_user_model().objects.get(username='normal_user')
        sent_mails = len(mail.outbox)

        for i in range(0, vendor.clicks_limit - 1):
            get_model('statistics', 'ProductStat').objects.create(product=product.product_name, page="BuyReferral",
                                                                  user_id=user.id, vendor=vendor.name,
                                                                  ip=ip, created=datetime.date.today())
        management.call_command('check_clicks_limit_per_vendor', verbosity=0, interactive=False)
        vendor = get_model('apparel', 'Vendor').objects.get(pk=2)  # get updated instance of vendor
        self.assertFalse(vendor.is_limit_reached)
        self.assertGreaterEqual(len(mail.outbox), sent_mails)

    def test_clicks_limit_per_vendor_exceeded_custom_value(self):
        """
        Test an email is  sent to the admins when a limit is exceeded and limit
        of clicks has been defined
        """
        ip = "192.128.2.3"
        vendor = get_model('apparel', 'Vendor').objects.get(pk=2)
        product = get_model('apparel', 'Product').objects.get(slug='brand-cpc-product')
        user = get_user_model().objects.get(username='normal_user')
        sent_mails = len(mail.outbox)
        for i in range(0, vendor.clicks_limit):
            get_model('statistics', 'ProductStat').objects.create(product=product.product_name, page="BuyReferral",
                                                                  user_id=user.id, vendor=vendor.name,
                                                                  ip=ip, created=datetime.date.today())
        self.assertFalse(vendor.is_limit_reached)
        management.call_command('check_clicks_limit_per_vendor')

        vendor = get_model('apparel', 'Vendor').objects.get(pk=2)  # get updated instance of vendor
        self.assertTrue(vendor.is_limit_reached)
        self.assertGreaterEqual(len(mail.outbox), sent_mails + 1)

        # Check that an email is only sent one time

        for i in range(0, vendor.clicks_limit):
            get_model('statistics', 'ProductStat').objects.create(product=product.product_name, page="BuyReferral",
                                                                  user_id=user.id, vendor=vendor.name,
                                                                  ip=ip, created=datetime.date.today())
        self.assertTrue(vendor.is_limit_reached)
        management.call_command('check_clicks_limit_per_vendor')

        vendor = get_model('apparel', 'Vendor').objects.get(pk=2)  # get updated instance of vendor
        self.assertGreaterEqual(len(mail.outbox), sent_mails + 1)


    def test_clicks_limit_per_vendor_exceeded_default_value(self):
        """
        Test an email is  sent to the admins when a limit is exceeded and limit
        of clicks has not been defined
        """
        product = get_model('apparel', 'Product').objects.get(slug='brand-cpc-other-product-no-limit')
        vendor = get_model('apparel', 'Vendor').objects.get(pk=3)
        user = get_user_model().objects.get(username='normal_user')
        ip = "192.128.2.3"
        sent_mails = len(mail.outbox)
        for i in range(0, settings.APPAREL_DEFAULT_CLICKS_LIMIT):
            get_model('statistics', 'ProductStat').objects.create(product=product.product_name, page="BuyReferral",
                                                                  user_id=user.id, vendor=vendor.name,
                                                                  ip=ip, created=datetime.date.today())
        self.assertFalse(vendor.is_limit_reached)
        management.call_command('check_clicks_limit_per_vendor')
        vendor = get_model('apparel', 'Vendor').objects.get(pk=3)  # get updated instance of vendor
        self.assertTrue(vendor.is_limit_reached)
        self.assertGreaterEqual(len(mail.outbox), sent_mails + 1)
