import datetime
import decimal
import calendar
import logging

from dateutil.relativedelta import *
from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.core import management, mail
from django.conf import settings

from apparelrow.statistics.tasks import product_buy_click
from factories import *
from apparelrow.statistics.models import ProductStat
from apparelrow.statistics.utils import check_vendor_has_reached_limit, extract_short_link_from_url, is_ip_banned
from apparelrow.dashboard.utils import parse_date

log = logging.getLogger(__name__)


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
        cpc_vendor.locations.create(code='SE')

        get_model('dashboard', 'Cut').objects.create(cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, group=group,
                                                     vendor=cpc_vendor)
        self._login()

    @override_settings(GEOIP_DEBUG=True, GEOIP_RETURN_LOCATION="NO")
    def test_click_is_not_valid(self):
        """
        Tests that when a click ip does not match the market of the cpc store, the click is not valid
        and it will not be included in earnings
        """
        user = get_user_model().objects.get(username='normal_user')
        product = get_model('apparel', 'Product').objects.get(slug='brand-cpc-product')

        response = self.client.post(reverse('product-track', args=[product.pk, 'Ext-Link', user.pk]), follow=True,
                                    REMOTE_ADDR="190.104.96.3")

        total_clicks = get_model('statistics', 'ProductStat').objects.count()
        self.assertEqual(total_clicks, 1)
        valid_clicks = get_model('statistics', 'ProductStat').objects.filter(is_valid=True).count()
        self.assertEqual(valid_clicks, 0)
        str_date = datetime.date.today().strftime('%Y-%m-%d')
        management.call_command('clicks_summary', date=str_date, verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 0)
        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 0)


    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="SE")
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

    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="SE")
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
            log.info("Testing product %s for default vendor, Vendor [%s]" % (product,product.default_vendor.vendor.name))
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

    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="DK",DEFAULT_VENDOR_LOCATION=["ALL","SE","NO","US"])
    def test_valid_clicks_location(self):

        # Vendor Market: ["DK"]
        vendor = VendorFactory.create(name="PPC Vendor DK", is_cpc=True, is_cpo=False)
        vendor.locations.create(code='DK')
        product = ProductFactory.create(slug="product")
        VendorProductFactory.create(vendor=vendor, product=product)

        clicks = 10
        for i in range(clicks):
            ProductStatFactory.create(ip="1.2.3.4", vendor=vendor.name, product=product.slug)

        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=product.slug).count(), clicks)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=product.slug, is_valid=True).count(), clicks)

        # Vendor Market: ["ALL","SE","NO","US"]
        all_vendor = VendorFactory.create(name="PPC Vendor default", is_cpc=True, is_cpo=False)
        other_product = ProductFactory.create(slug='other-product')
        VendorProductFactory.create(vendor=all_vendor, product=other_product)

        for i in range(clicks):
            ProductStatFactory.create(ip="5.6.7.8", vendor=all_vendor.name, product=other_product.slug)

        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=product.slug).count(), clicks)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=other_product.slug, is_valid=True).count(), 0)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=other_product.slug, is_valid=False).count(), clicks)

    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="ALL",DEFAULT_VENDOR_LOCATION=["ALL","SE","NO","US"])
    def test_clicks_from_unmapped_location(self):

        # Vendor Market: ["DK"]
        vendor = VendorFactory.create(name="PPC Vendor DK", is_cpc=True, is_cpo=False)
        vendor.locations.create(code='DK')
        product = ProductFactory.create(slug="product")
        VendorProductFactory.create(vendor=vendor, product=product)

        clicks = 1
        for i in range(clicks):
            ProductStatFactory.create(ip="1.2.3.4", vendor=vendor.name, product=product.slug)

        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=product.slug).count(), clicks)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=product.slug, is_valid=True).count(), 0)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=product.slug, is_valid=False).count(), 1)

        # Vendor Market: ["ALL","SE","NO","US"]
        all_vendor = VendorFactory.create(name="PPC Vendor default", is_cpc=True, is_cpo=False)
        other_product = ProductFactory.create(slug='other-product')
        VendorProductFactory.create(vendor=all_vendor, product=other_product)

        for i in range(clicks):
            ProductStatFactory.create(ip="5.6.7.8", vendor=all_vendor.name, product=other_product.slug)

        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=product.slug).count(), clicks)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=other_product.slug, is_valid=True).count(), clicks)
        self.assertEqual(get_model('statistics', 'ProductStat').objects.filter(product=other_product.slug, is_valid=False).count(), 0)

    def test_check_vendor_has_reached_limit(self):
        vendor = get_model('apparel', 'Vendor').objects.get(pk=4)
        start_date, end_date = parse_date(None, None)

        has_reached_limit = check_vendor_has_reached_limit(vendor, start_date, end_date)
        user = get_user_model().objects.get(username='normal_user')
        ip = "192.128.2.3"

        self.assertFalse(vendor.is_limit_reached)
        self.assertFalse(has_reached_limit)

        product = get_model('apparel', 'Product').objects.get(slug='brand-cpc-other-product-test-limit-reached')
        for i in range(0, vendor.clicks_limit+1):
            get_model('statistics', 'ProductStat').objects.create(product=product.product_name, page="BuyReferral",
                                                                  user_id=user.id, vendor=vendor.name,
                                                                  ip=ip, created=datetime.date.today())

        has_reached_limit = check_vendor_has_reached_limit(vendor, start_date, end_date)
        self.assertTrue(vendor.is_limit_reached)
        self.assertTrue(has_reached_limit)

        # Test the value is reset
        next_month_start = start_date + relativedelta(months=1)
        next_month_end = next_month_start
        next_month_end = next_month_end.replace(day=calendar.monthrange(next_month_start.year, 12)[1], month=12)
        has_reached_limit = check_vendor_has_reached_limit(vendor, next_month_start, next_month_end)

        self.assertFalse(vendor.is_limit_reached)
        self.assertFalse(has_reached_limit)

    def test_update_stats_referer(self):
        referer_1 = "http://petra.metromode.se/page/2/"
        short_link = "http://apprl.com/sv/redirect/3588280/Ext-Link/28554/"
        product_stat_1 = ProductStatFactory.create(ip="5.6.7.8", referer='%s\n%s'%(referer_1, short_link))

        referer_2 = "http://content.apparelrow.com/embed/look/1af23c56ca184d7994b199ece271a9d5/gina-tricot-2-5/?host=http%3A%2F%2Febbazingmark.com"
        short_link = "http://content.apparelrow.com/sv/redirect/3614195/Ext-Look/30722/"
        product_stat_2 = ProductStatFactory.create(ip="5.6.7.8", referer='%s\n%s'%(referer_2, short_link))

        product_stat_3 = ProductStatFactory.create(ip="5.6.7.8", referer="")

        management.call_command('update_stats_referer', verbosity=0, interactive=False, skip_progress=True)

        # Referer link
        updated_product_stat_1 = ProductStat.objects.get(id=product_stat_1.id)
        self.assertEqual(updated_product_stat_1.referer, referer_1)

        # Longer referer link
        updated_product_stat_2 = ProductStat.objects.get(id=product_stat_2.id)
        self.assertEqual(updated_product_stat_2.referer, referer_2)

        # Blank referer link
        updated_product_stat_3 = ProductStat.objects.get(id=product_stat_3.id)
        self.assertEqual(updated_product_stat_3.referer, "")

    def test_product_buy_click(self):
        """
        Disclaimer: This test is not yet done. It originated from reports of certain domain deeplinks not working and getting
        improperly populated by affiliate network. https://www.pivotaltracker.com/story/show/135521791
        :return:
        """

        # product_buy_click(product_id, referer, client_referer, ip, user_agent, user_id, page, cookie_already_exists)
        # _, _, _, source_link = parse_sid(result['sid'])
        # TypeError: 'NoneType' object has no attribute '__getitem__'
        # TODO: Resolve why this is happening, this test just makes sure it prevents the crasch when this occurs.
        original_url = "http://www.cafe.se/vinterns-snyggaste-jacka-10-shearlingjackor-du-kan-kopa-redan-idag/"
        vendor_name = "Jerkstore"
        vendor = VendorFactory.create(name=vendor_name)
        domain_deep_link = DomainDeepLinkingFactory.create(vendor=vendor, domain="www.jerkstore.com")
        self.assertEquals(domain_deep_link.template, "http://apprl.com/a/link/?store_id=jerkstore&custom={sid}&url={url}")
        domain_link = ShortDomainLinkFactory.create(url=original_url, vendor=vendor)
        user = domain_link.user
        link = domain_link.link()
        self.assertIsNotNone( link )
        full_link = reverse('domain-short-link', args=[link])
        self.assertTrue( full_link.startswith("/pd/") )
        self.assertFalse(ProductStat.objects.count())
        for i in range(5):
            product_buy_click(u'0', u'http://www.cafe.se/vinterns-snyggaste-jacka-10-shearlingjackor-du-kan-kopa-redan-idag/',
                          full_link, '193.61.179.9', 'Mozilla/5.0 (Safari/601.6.17)', str(user.pk), u'Ext-Link', False)
        self.assertEquals(ProductStat.objects.filter(user_id=user.pk).count(), 5)

        short_link = extract_short_link_from_url(full_link)
        _, returned_vendor_name, _ = ShortDomainLink.objects.get_short_domain_for_link(short_link)
        self.assertTrue(returned_vendor_name == domain_link.vendor.name)
        source_link = ShortDomainLink.objects.get_original_url_for_link(short_link)

        self.assertEquals(source_link, "LINK-NOT-FOUND")
        product_buy_click(u'0',
                          u'http://www.cafe.se/vinterns-snyggaste-jacka-10-shearlingjackor-du-kan-kopa-redan-idag/',
                          full_link, '193.61.179.9', 'Mozilla/5.0 (Safari/601.6.17)', str(666), u'Ext-Link', False)

    def test_is_ip_banned(self):
        """
        This test only works if there is a valid cache backend. Dummy cache which is not storing any values will make it fail.
        :return:
        """
        from django.core.cache import get_cache
        cache = get_cache("default")
        cache.delete(settings.PRODUCTSTAT_IP_QUARANTINE_KEY)
        banned_ips = ["1.2.3.4", "5.6.7.8"]
        cache.set(settings.PRODUCTSTAT_IP_QUARANTINE_KEY, banned_ips, 60*5)
        cached_ips = cache.get(settings.PRODUCTSTAT_IP_QUARANTINE_KEY)
        self.assertEquals(banned_ips, cached_ips)

        testing_ips = [("123.234.123.123", False), ("1.2.3.4", True), ("11.21.31.41", False), ("5.6.7.9", False),
                       ("5.6.7.8", True)]

        for ip, result in testing_ips:
            self.assertEquals(is_ip_banned(ip), result, "The ip {} does not give the correct result.".format(ip))
        cache.delete(settings.PRODUCTSTAT_IP_QUARANTINE_KEY)

    #@override_settings(BLOCKED_USER_AGENTS=[])
    def test_check_contains_invalid_user_agents(self):
        vendor = VendorFactory.create(name="jerkstore")
        original_url = "http://www.cafe.se/vinterns-snyggaste-jacka-10-shearlingjackor-du-kan-kopa-redan-idag/"
        domain_deep_link = DomainDeepLinkingFactory.create(vendor=vendor, domain="www.jerkstore.com")
        self.assertEquals(domain_deep_link.template, "http://apprl.com/a/link/?store_id=jerkstore&custom={sid}&url={url}")
        domain_link = ShortDomainLinkFactory.create(url=original_url, vendor=vendor)
        user = domain_link.user
        link = domain_link.link()
        self.assertIsNotNone( link )
        full_link = reverse('domain-short-link', args=[link])
        self.assertEquals(domain_deep_link.template, "http://apprl.com/a/link/?store_id=jerkstore&custom={sid}&url={url}")
        instagram_user_agents = [u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Mobile/14G60 Instagram 12.0.0.16.90 (iPhone6,2; iOS 10_3_3; da_DK; da-DK; scale=2.00; gamut=normal; 640x1136)',
                                  u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Mobile/14G60 Instagram 12.0.0.16.90 (iPhone9,3; iOS 10_3_3; sv_SE; sv-SE; scale=2.00; gamut=wide; 750x1334)', u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_1_1 like Mac OS X) AppleWebKit/602.2.14 (KHTML, like Gecko) Mobile/14B100 Instagram 11.0.0.21.20 (iPhone7,2; iOS 10_1_1; sv_SE; sv-SE; scale=2.00; gamut=normal; 750x1334)', u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Mobile/14G60 Instagram 12.0.0.16.90 (iPhone9,3; iOS 10_3_3; nb_NO; nb-NO; scale=2.34; gamut=wide; 750x1331)', u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_2 like Mac OS X) AppleWebKit/603.2.4 (KHTML, like Gecko) Mobile/14F89 Instagram 10.28.0 (iPhone7,2; iOS 10_3_2; da_DK; da-DK; scale=2.00; gamut=normal; 750x1334)',
                                  u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Mobile/14E304 Instagram 12.0.0.16.90 (iPhone8,4; iOS 10_3_1; sv_SE; sv-SE; scale=2.00; gamut=normal; 640x1136)',
                                  u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Mobile/14G60 Instagram 12.0.0.16.90 (iPhone9,3; iOS 10_3_3; sv_SE; sv-SE; scale=2.00; gamut=wide; 750x1334)',
                                  u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_2_1 like Mac OS X) AppleWebKit/602.4.6 (KHTML, like Gecko) Mobile/14D27 Instagram 12.0.0.16.90 (iPhone9,3; iOS 10_2_1; sv_SE; sv-SE; scale=2.00; gamut=wide; 750x1334)',
                                  u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Mobile/14G60 Instagram 12.0.0.16.90 (iPhone8,1; iOS 10_3_3; sv_SE; sv-SE; scale=2.00; gamut=normal; 750x1334)',
                                  u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_0_2 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) Mobile/14A456 Instagram 12.0.0.16.90 (iPhone8,1; iOS 10_0_2; sv_SE; sv-SE; scale=2.00; gamut=normal; 750x1334)']

        facebook_user_agents = [u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_2_1 like Mac OS X) AppleWebKit/602.4.6 (KHTML, like Gecko) Mobile/14D27 [FBAN/FBIOS;FBAV/135.0.0.45.90;FBBV/66877072;FBDV/iPhone9,3;FBMD/iPhone;FBSN/iOS;FBSV/10.2.1;FBSS/2;FBCR/TELIA;FBID/phone;FBLC/sv_SE;FBOP/5;FBRV/0]',
                                u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Mobile/14G60 [FBAN/FBIOS;FBAV/139.0.0.46.90;FBBV/70207865;FBDV/iPhone7,2;FBMD/iPhone;FBSN/iOS;FBSV/10.3.3;FBSS/2;FBCR/TELIA;FBID/phone;FBLC/sv_SE;FBOP/5;FBRV/0]',
                                u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_0_2 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) Mobile/14A456 [FBAN/FBIOS;FBAV/66.0.0.42.70;FBBV/40764466;FBRV/0;FBDV/iPhone8,1;FBMD/iPhone;FBSN/iOS;FBSV/10.0.2;FBSS/2;FBCR/Tele2;FBID/phone;FBLC/sv_SE;FBOP/5]',
                                u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Mobile/14G60 [FBAN/FBIOS;FBAV/139.0.0.46.90;FBBV/70207865;FBDV/iPhone8,1;FBMD/iPhone;FBSN/iOS;FBSV/10.3.3;FBSS/2;FBCR/Telenor;FBID/phone;FBLC/sv_SE;FBOP/5;FBRV/0]']

        twitter_user_agents = [u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_2_1 like Mac OS X) AppleWebKit/602.3.12 (KHTML, like Gecko) Mobile/14D27 Twitter for iPhone',
                               u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_2_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Mobile/14D27 Twitter for iPhone',
                               u'Mozilla/5.0 (iPad; CPU OS 10_3_1 like Mac OS X) AppleWebKit/602.3.12 (KHTML, like Gecko) Mobile/14E304 Twitter for iPhone']

        random_user_agents = [u'Mozilla/5.0 (Linux; Android 6.0.1; SAMSUNG SM-G900F Build/MMB29M) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/5.4 Chrome/51.0.2704.106 Mobile Safari/537.36',
                              u'Mozilla/5.0 (Windows NT 6.1;Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
                              u'Mozilla/5.0 (iPad; CPU OS 9_3_5 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13G36 Safari/601.1',
                              u'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
                              u'Mozilla/5.0 (Linux; Android 5.0.1; YOGA Tablet 2-1050FBuild/LRX22C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.107 Safari/537.36',
                              u'Mozilla/5.0 (iPad; CPU OS 10_2_1 like Mac OS X) AppleWebKit/602.4.6 (KHTML, like Gecko) Version/10.0 Mobile/14D27 Safari/602.1',
                              u'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.0 Mobile/14G60 Safari/602.1']
        user = UserFactory.create()
        list_of_agents = [("Instagram", instagram_user_agents), ("Facebook", facebook_user_agents), ("Twitter", twitter_user_agents)]
        for name, agents in list_of_agents:
            ProductStat.objects.all().delete()
            self.assertEquals(ProductStat.objects.count(), 0)
            for user_agent in agents:
                product_buy_click(u'0', original_url, full_link, '193.61.179.9', user_agent, user.pk, u'Ext-Link', False)
            log.info("Checking {} links.".format(name))
            self.assertEquals(ProductStat.objects.count(), len(agents))
            self.assertEquals(ProductStat.objects.filter(is_valid=True).count(), 0)
        ProductStat.objects.all().delete()
        self.assertEquals(ProductStat.objects.count(), 0)

        for user_agent in random_user_agents:
            product_buy_click(u'0', original_url, full_link, '193.61.179.9', user_agent, user.pk, u'Ext-Link', False)
        self.assertEquals(ProductStat.objects.count(), len(random_user_agents))
        self.assertEquals(ProductStat.objects.filter(is_valid=True).count(), len(random_user_agents))

        ProductStat.objects.all().delete()
        product_buy_click(u'0', original_url, full_link, '193.61.179.9', None, user.pk, u'Ext-Link', False)
        self.assertEquals(ProductStat.objects.filter(is_valid=True).count(), 0)
        self.assertEquals(ProductStat.objects.count(), 1)