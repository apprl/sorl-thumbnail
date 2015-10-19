import datetime
import decimal
from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.core.urlresolvers import reverse
from django.core import management, mail
from django.conf import settings
from factories import *



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

    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="SE",VENDOR_LOCATION_MAPPING={"default":["ALL","SE","NO","US"],})
    def test_unique_clicks_per_day(self):
        """
        Tests that only one click could be made to the same product from the same browser, once a day
        """

        # Test with a vendor with default location so no need to pass IP
        vendor_all = VendorFactory.create(name="CPC Vendor default market", is_cpc=True, is_cpo=False)

        products = [ProductFactory.create() for i in range(20)]
        for index, product in enumerate(products):
            VendorProductFactory.create(product=product,vendor=vendor_all)
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

        # Creating 20 different clicks and check id it works. Every click is valid since it is different products.
        for product in products:
            response = self.client.post(reverse('product-track', args=[product.pk, 'Ext-Link', user.pk]), follow=True)
        response = self.client.post(reverse('product-track', args=[products[0].pk, 'Ext-Link', user.pk]), follow=True)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.count(), 3+20+1)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(is_valid=True).count(), 2+20)

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

    def test_extract_short_link_from_url(self):
        from apparelrow.statistics.utils import extract_short_link_from_url
        url = u'/s/4C90/234/'
        self.assertEquals("4C90", extract_short_link_from_url(url, 234))
        short_url = u'/s/4C91/'
        self.assertEquals("4C91", extract_short_link_from_url(short_url))
        short_url_locale_1 = u'en/s/4C92/'
        self.assertEquals("4C92", extract_short_link_from_url(short_url_locale_1))
        short_url_locale_2 = u'/sv/s/4C93/'
        self.assertEquals("4C93", extract_short_link_from_url(short_url_locale_2))
        short_url_locale_3 = u'en/s/4C94/123'
        self.assertEquals("4C94", extract_short_link_from_url(short_url_locale_3, 123))
        short_url_locale_4 = u'/sv/s/4C95/456'
        self.assertEquals("4C95", extract_short_link_from_url(short_url_locale_4,456))
        short_url_locale_5 = u'http://staging.apprl.com/sv/s/4C96/'
        self.assertEquals("4C96", extract_short_link_from_url(short_url_locale_5))

    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="NO",VENDOR_LOCATION_MAPPING={"PPC Vendor SE":["SE"], "default":["ALL","SE","NO","US"],})
    def test_valid_clicks_location(self):
        ip_pool = ()

        # ALL
        for index in range(0,10):
            ip_pool += ('194.224.40.17%s' % index,)
        # NO
        for index in range(0,10):
            ip_pool += ('2.150.59.15%s' % index,)
        # US
        for index in range(0,10):
            ip_pool += ('66.249.64.15%s' % index,)
        # SE
        for index in range(0,10):
            ip_pool += ('109.104.22.8%s' % index,)

        # Vendor Market: ["SE"]
        vendor = VendorFactory.create(name="PPC Vendor SE", is_cpc=True, is_cpo=False)
        product = ProductFactory.create(slug="product")
        VendorProductFactory.create(vendor=vendor, product=product)

        for ip in ip_pool:
            ProductStatFactory.create(ip=ip, vendor=vendor.name, product=product.slug)

        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=product.slug).count(), len(ip_pool))
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=product.slug, is_valid=True).count(), 10)

        # Vendor Market: ["ALL","SE","NO","US"]
        all_vendor = VendorFactory.create(name="PPC Vendor default", is_cpc=True, is_cpo=False)
        other_product = ProductFactory.create(slug='other-product')
        VendorProductFactory.create(vendor=all_vendor, product=other_product)

        for ip in ip_pool:
            ProductStatFactory.create(ip=ip, vendor=all_vendor.name, product=other_product.slug)

        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=product.slug).count(), len(ip_pool))
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=other_product.slug, is_valid=True).count(), len(ip_pool))



