import datetime
import decimal
from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.core.urlresolvers import reverse
from django.core import management
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

    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="NO",VENDOR_LOCATION_MAPPING={"CPC Vendor":["SE"], "default":["ALL","SE","NO","US"],})
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

    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="NO",VENDOR_LOCATION_MAPPING={"CPC Vendor":["SE"], "default":["ALL","SE","NO","US"],})
    def test_locality_clicks_are_valid(self):
        """
        Tests that when a click ip does  match the market of the cpc store, the click is valid and it will be included
        in earnings
        """
        user = get_user_model().objects.get(username='normal_user')
        product = get_model('apparel', 'Product').objects.get(slug='brand-cpc-product')
        clickcost = get_model('dashboard', 'ClickCost').objects.get(pk=1)
        for i in range(10):
            response = self.client.post(reverse('product-track', args=[product.pk, 'Ext-Link', user.pk]), follow=True,
                                    REMOTE_ADDR="192.1.1.1.")

        valid_clicks = get_model('statistics', 'ProductStat').objects.filter(is_valid=True).count()
        self.assertEqual(valid_clicks, 0)
        total_clicks = get_model('statistics', 'ProductStat').objects.count()
        self.assertEqual(total_clicks, 10)

    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="SE",VENDOR_LOCATION_MAPPING={"CPC Vendor":["SE"], "default":["ALL","SE","NO","US"],})
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

    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="SE",VENDOR_LOCATION_MAPPING={"CPC Vendor SE":["SE"],"CPC Vendor NO":["NO"], "default":["ALL","SE","NO","US"],})
    def test_unique_clicks_per_day(self):
        """
        Tests that only one click could be made to the same product from the same browser, once a day
        """
        from apparelrow.apparel.factories import ProductFactory,VendorFactory,VendorProductFactory
        vendor_se = VendorFactory.create(name="CPC VENDOR SE")
        vendor_no = VendorFactory.create(name="CPC VENDOR NO")
        vendors = [vendor_se,vendor_no]
        products = [ProductFactory.create() for i in range(20)]
        for index, product in enumerate(products):
            selector = divmod(index,2)[1]
            VendorProductFactory.create(product=product,vendor=vendors[selector])
        for product in products:
            print "Testing product %s for default vendor, Vendor [%s]" % (product,product.default_vendor.vendor.name)
            self.assertIsNotNone(product.default_vendor)

        user = get_user_model().objects.get(username='normal_user')
        product = get_model('apparel', 'Product').objects.get(slug='brand-product')
        other_product = get_model('apparel', 'Product').objects.get(slug='brand-other-product')
        response = self.client.post(reverse('product-track', args=[product.pk, 'Ext-Link', user.pk]), follow=True)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.count(), 1)

        # Doing the same request shouldn't created another click
        response = self.client.post(reverse('product-track', args=[product.pk, 'Ext-Link', user.pk]), follow=True)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.count(), 2)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(is_valid=True).count(), 1)

        # Click other product should generate a new click
        response = self.client.post(reverse('product-track', args=[other_product.pk, 'Ext-Link', user.pk]), follow=True)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.count(), 3)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(is_valid=True).count(), 2)

        # Creating 20 different clicks and check id it works
        for product in products:
            response = self.client.post(reverse('product-track', args=[product.pk, 'Ext-Link', user.pk]), follow=True)
        response = self.client.post(reverse('product-track', args=[products[0].pk, 'Ext-Link', user.pk]), follow=True)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.count(), 3+20+1)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(is_valid=True).count(), 2+10)