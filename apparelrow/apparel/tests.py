import json
from apparelrow.apparel.views import product_lookup_asos_nelly
import unittest

from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from decimal import Decimal
from django.conf import settings
from apparelrow.apparel.models import Shop, ShopEmbed

from django.core.urlresolvers import reverse
from django.test import TestCase
from apparelrow.apparel.models import Product, ProductLike
from apparelrow.profile.models import User
from apparelrow.dashboard.models import Group
from django.test import Client
from factories import *

""" CHROME EXTENSION """
@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestChromeExtension(TestCase):

    def setUp(self):
        domaindeeplinks = [("nelly.com","Nelly"),
        ("www.luisaviaroma.com","Luisaviaroma"),
        ("www.mrporter.com","Mr Porter"),
        ("www.theoutnet.com","The Outnet"),
        ("www.ssense.com","SSENSE"),
        ("www.oki-ni.com","Oki-Ni"),
        ("www.asos.com","ASOS"),
        ("www.net-a-porter.com","Net-a-Porter"),
        ("www.vrients.com","Vrients"),
        ("www.minimarket.se","Minimarket"),
        ("elevenfiftynine.se","Elevenfiftynine"),
        ("www.carinwester.com","Carin Wester"),
        ("www.mq.se","MQ"),
        ("www.jc.se","JC"),
        ("www.wolfandbadger.com","Wolf & Badger"),
        ("shirtonomy.se","Shirtonomy"),
        ("eleven.se","Eleven"),
        ("www.menlook.com","Menlook"),
        ("www.philipb.com","Philip B"),
        ("altewaisaome.com","Altewaisaome"),
        ("www.laurenbbeauty.com","Lauren B"),
        ("www.houseofdagmar.se","Dagmar"),
        ("www.qvc.com","QVC"),
        ("www.filippa-k.com/se","Filippa K"),
        ("www.boozt.com/se","Boozt se"),
        ("www.boozt.com/no","Boozt no"),
        ("www.monicavinader.com","Monica Vinader"),
        ("www.aldoshoes.com","ALDO"),
        ("www.gramshoes.com","Gram Shoes"),
        ("confidentliving.se","ConfidentLiving"),
        ("www.room21.no","Room 21 no"),
        ("www.rum21.se","Rum 21 se"),
        ("example.com","Example")]
        for domain,vendor in domaindeeplinks:
            ddl = DomainDeepLinkingFactory.create(domain=domain,vendor__name=vendor,template='http://example.com/my-template')
            #print "Creating DomainDeeplinking %s, %s " % (ddl.id,ddl.domain)


    def _login(self):
        normal_user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        is_logged_in = self.client.login(username='normal_user', password='normal')
        self.assertTrue(is_logged_in)

    def test_not_authenticated(self):
        response = self.client.get('/backend/authenticated/')
        json_content = json.loads(response.content)

        self.assertEqual(json_content['profile'], None)
        self.assertEqual(json_content['authenticated'], False)

    def test_authenticated(self):
        self._login()

        response = self.client.get('/backend/authenticated/')
        json_content = json.loads(response.content)

        self.assertEqual(json_content['profile'], u'http://testserver/profile/normal_user/')
        self.assertEqual(json_content['authenticated'], True)

    def test_product_lookup_not_logged_in(self):
        response = self.client.get('/backend/product/lookup/?key=not_found_url&domain=example.com')
        self.assertEqual(response.status_code, 404)

    def test_product_lookup_not_found(self):
        self._login()

        response = self.client.get('/backend/product/lookup/?key=not_found_url&domain=weird.com')
        self.assertEqual(response.status_code, 404)


    """def test_product_lookups(self):
        product0 = ProductFactory.create(product_key="http://shirtonomy.se/skjortor/white-twill")
        product1 = ProductFactory.create(product_key="http://shirtonomy.se/skjortor/sky-twill")
        product2 = ProductFactory.create(product_key="http://shirtonomy.se/skjortor/blue-twill")
        self.assertIsNotNone(product0.product_name)
        self.assertIsNotNone(product0.id)
        vendor0 = VendorFactory.create()
        vendor1 = VendorFactory.create()
        vendor2 = VendorFactory.create()
        print vendor1
        vendor = NellyVendorWithProductFactory()
        for product in vendor.product_set.all():
            print product
        vendor = AsosVendorWithProductFactory()
        for product in vendor.product_set.all():
            print product
        #print product.default_vendor
    """

    def test_product_lookup_by_domain(self):
        self._login()

        vendor = get_model('apparel', 'Vendor').objects.create(name='Vendor')
        get_model('apparel', 'DomainDeepLinking').objects.create(
            vendor=vendor,
            domain='example.com/se',
            template='http://example.com/my-template'
        )

        response = self.client.get('/backend/product/lookup/?key=http://example.com/se/shoes?product=123&domain=example.com')
        self.assertEquals(response.status_code,200)
        json_content = json.loads(response.content)

        self.assertEqual(json_content['product_pk'], None)
        self.assertEqual(json_content['product_link'], None)
        self.assertEqual(json_content['product_short_link'], 'http://testserver/pd/4C92/')
        self.assertEqual(json_content['product_liked'], False)


    def test_product_lookup_by_url(self):
        self._login()

        vendor = get_model('apparel', 'Vendor').objects.create(name='Vendor')
        category = get_model('apparel', 'Category').objects.create(name='Category')
        manufacturer = get_model('apparel', 'Brand').objects.create(name='Brand')
        product_key = 'http://example.com/example?someproduct=12345'
        product = get_model('apparel', 'Product').objects.create(
            product_name='Product',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True,
            product_key=product_key
        )
        """product = ProductFactory.create(
            product_name='Product',
            #category=category,
            manufacturer__name="manufacturer",
            gender='M',
            product_image='no real image',
            published=True,
            product_key=product_key
        )"""

        print "Creating product %s,%s" % (product.id,product)
        print "Product key is %s" % (product.product_key)
        #print "Creating Domain Deeplinking %s, domain %s" % (ddl,ddl.domain)
        self.assertIsNotNone( product.id )
        response = self.client.get('/backend/product/lookup/?key=%s' % product_key)
        self.assertEqual(response.status_code, 200)
        json_content = json.loads(response.content)

        self.assertEqual(json_content['product_pk'], product.id)
        self.assertEqual(json_content['product_link'], 'http://testserver/products/product/')
        self.assertEqual(json_content['product_short_link'], 'http://testserver/p/4C92/')
        self.assertEqual(json_content['product_liked'], False)

class TestChromeExtensionSpecials(TestCase):
    fixtures = ['extensiontest_vendor.json', 'extensiontest_product.json']

    def _login(self):
        normal_user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        is_logged_in = self.client.login(username='normal_user', password='normal')
        self.assertTrue(is_logged_in)

    def test_fixtures(self):
        self._login()

        vendor = get_model('theimp', 'Vendor').objects.get(name='asos')
        product = get_model('theimp', 'Product').objects.get(pk=883414)

        self.assertIsNotNone(vendor)
        self.assertIsNotNone(product)

    def test_product_asos_nelly_luisaviaroma(self):
        #1st ASOS product
        #original
        key = "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2108486&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlw&istBid=t&channelref=affiliate"
        self.assertEqual(product_lookup_asos_nelly(key), 883414)
        #after click
        key = "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2108486&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlw&istBid=t&channelref=affiliate&r=2"
        self.assertEqual(product_lookup_asos_nelly(key), 883414)
        #manual search
        key = "http://www.asos.com/asos/asos-vest-with-extreme-racer-back/prod/pgeproduct.aspx?iid=2108486&clr=Grey&SearchQuery=Vest+With+Extreme+Racer+Back&pgesize=36&pge=1&totalstyles=101&gridsize=3&gridrow=2&gridcolumn=3"
        self.assertEqual(product_lookup_asos_nelly(key), 883414)
        #from "last viewed"
        key = "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2108486&CTARef=Recently%20Viewed"
        self.assertEqual(product_lookup_asos_nelly(key), 883414)

        #2nd ASOS product
        #original
        key = "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2109266&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlq&istBid=t&channelref=affiliate"
        self.assertEqual(product_lookup_asos_nelly(key), 883415)
        #after click
        key = "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2109266&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlq&istBid=t&channelref=affiliate"
        self.assertEqual(product_lookup_asos_nelly(key), 883415)
        #manual search
        key = "http://www.asos.com/asos/asos-vest-with-extreme-racer-back/prod/pgeproduct.aspx?iid=2109266&clr=White&SearchQuery=Vest+With+Extreme+Racer+Back&pgesize=36&pge=1&totalstyles=100&gridsize=3&gridrow=2&gridcolumn=2"
        self.assertEqual(product_lookup_asos_nelly(key), 883415)

        #3rd ASOS product
        #original
        key = "http://www.asos.com/ASOS/ASOS-Mix-and-Match-Halter-Leopard-Print-Bikini-Top/Prod/pgeproduct.aspx?iid=2125546&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=witimippa&istBid=t&channelref=affiliate"
        self.assertEqual(product_lookup_asos_nelly(key), 883416)
        #after click
        key = "http://www.asos.com/ASOS/ASOS-Mix-and-Match-Halter-Leopard-Print-Bikini-Top/Prod/pgeproduct.aspx?iid=2125546&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=witimippa&istBid=t&channelref=affiliate"
        self.assertEqual(product_lookup_asos_nelly(key), 883416)
        #manual search
        key = "http://www.asos.com/asos/asos-mix-and-match-halter-leopard-print-bikini-top/prod/pgeproduct.aspx?iid=2125546&clr=Leopardprint&SearchQuery=Mix+and+Match+Halter+Leopard+Print+Bikini+Top&SearchRedirect=true"
        self.assertEqual(product_lookup_asos_nelly(key), 883416)

        #1st Luisaviaroma product
        #original
        key = "http://www.luisaviaroma.com/adidas+originals+by+mary+katrantzou/women/t-shirts/60I-CD1014/lang_EN"
        self.assertEqual(product_lookup_asos_nelly(key), 883598)
        #after click
        key = "http://www.luisaviaroma.com/index.aspx#ItemSrv.ashx|SeasonId=60I&CollectionId=CD1&ItemId=14&SeasonMemoCode=actual&GenderMemoCode=women&CategoryId=&SubLineId=clothing"
        self.assertEqual(product_lookup_asos_nelly(key), 883598)
        #manual search
        key = "http://www.luisaviaroma.com/index.aspx?#ItemSrv.ashx|SeasonId=60I&CollectionId=CD1&ItemId=14&VendorColorId=TTYzMDU30&SeasonMemoCode=actual&GenderMemoCode=women&CategoryId=&SubLineMemoCode="
        self.assertEqual(product_lookup_asos_nelly(key), 883598)

        #2nd Luisaviaroma product
        #original
        key = "http://www.luisaviaroma.com/adidas+originals+by+mary+katrantzou/women/skirts/60I-CD1013/lang_EN"
        self.assertEqual(product_lookup_asos_nelly(key), 883602)
        #after click
        key = "http://www.luisaviaroma.com/index.aspx#ItemSrv.ashx|SeasonId=60I&CollectionId=CD1&ItemId=13&SeasonMemoCode=actual&GenderMemoCode=women&CategoryId=&SubLineId=clothing"
        self.assertEqual(product_lookup_asos_nelly(key), 883602)
        #manual search
        key = "http://www.luisaviaroma.com/index.aspx?#ItemSrv.ashx|SeasonId=60I&CollectionId=CD1&ItemId=13&VendorColorId=TTYzMTAy0&SeasonMemoCode=actual&GenderMemoCode=women&CategoryId=&SubLineMemoCode="
        self.assertEqual(product_lookup_asos_nelly(key), 883602)

        #1st Nelly product
        #original
        key = "http://nelly.com/se/kl\u00e4der-f\u00f6r-kvinnor/kl\u00e4der/festkl\u00e4nningar/nly-trend-917/scuba-wrap-dress-917910-29/"
        self.assertEqual(product_lookup_asos_nelly(key), 883607)
        #after click
        key = "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/kl%C3%A4der/festkl%C3%A4nningar/nly-trend-917/scuba-wrap-dress-917910-29/"
        self.assertEqual(product_lookup_asos_nelly(key), 883607)
        #manual search
        key = "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/kl%C3%A4der/festkl%C3%A4nningar/nly-trend-917/scuba-wrap-dress-917910-29/"
        self.assertEqual(product_lookup_asos_nelly(key), 883607)

        #2nd Nelly product
        #original
        key = "http://nelly.com/se/kl\u00e4der-f\u00f6r-kvinnor/kl\u00e4der/festkl\u00e4nningar/closet-1153/quilt-effect-dress-601764-2350/"
        self.assertEqual(product_lookup_asos_nelly(key), 883603)
        #after click
        key = "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/kl%C3%A4der/festkl%C3%A4nningar/closet-1153/quilt-effect-dress-601764-2350/"
        self.assertEqual(product_lookup_asos_nelly(key), 883603)
        #manual search
        key = "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/kl%C3%A4der/festkl%C3%A4nningar/closet-1153/quilt-effect-dress-601764-2350/"
        self.assertEqual(product_lookup_asos_nelly(key), 883603)
        #made up category
        key = "http://nelly.com/se/somecategory/somesubcategory/otherparam/closet-1153/quilt-effect-dress-601764-2350/"
        self.assertEqual(product_lookup_asos_nelly(key), 883603)

        #3rd Nelly product from pivotaltracker story
        #original
        key = "http://nelly.com/se/skor-kvinna/skor/vardagsskor/nike-1013/wmns-nike-air-max-thea-118540-54/"
        self.assertEqual(product_lookup_asos_nelly(key), 883604)
        #other
        key = "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/skor/vardagsskor/nike-1013/wmns-nike-air-max-thea-118540-54"
        self.assertEqual(product_lookup_asos_nelly(key), 883604)


class TestProductDetails(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        self.vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        self.group = get_model('dashboard', 'Group').objects.create(name='mygroup')
        self.product = product = get_model('apparel', 'Product').objects.create()

        get_model('apparel', 'VendorProduct').objects.create(product=self.product, vendor=self.vendor)
        get_model('dashboard', 'Cut').objects.create(group=self.group, vendor=self.vendor,
                                                           cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT,
                                                           referral_cut=settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT)

    def test_product_details_aan_user_is_publisher(self):
        is_logged_in = self.client.login(username='normal_user', password='normal')
        self.assertTrue(is_logged_in)
        self.user.is_partner = True
        self.user.partner_group = self.group
        self.user.save()

        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=self.vendor)

        earning_product = self.product.get_product_earning(self.user)
        self.assertAlmostEqual(earning_product,
                               Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT)*Decimal(store.commission_percentage),
                               places=2)

    def test_product_details_aan_user_is_not_publisher(self):
        is_logged_in = self.client.login(username='normal_user', password='normal')
        self.assertTrue(is_logged_in)

        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=self.vendor)
        earning_product = self.product.get_product_earning(self.user)
        self.assertIsNone(earning_product)

    def test_product_details_external_user_is_publisher(self):
        is_logged_in = self.client.login(username='normal_user', password='normal')
        self.assertTrue(is_logged_in)
        self.user.is_partner = True
        self.user.partner_group = self.group
        self.user.save()

        get_model('dashboard', 'StoreCommission').objects.create(vendor=self.vendor,commission="6/10/0")

        earning_product = self.product.get_product_earning(self.user)
        self.assertAlmostEqual(earning_product,
                               Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT)*Decimal(0.08),
                               places=2)


    def test_product_details_external_user_is_not_publisher(self):
        is_logged_in = self.client.login(username='normal_user', password='normal')
        self.assertTrue(is_logged_in)
        get_model('dashboard', 'StoreCommission').objects.create(vendor=self.vendor,commission="6/10/0")

        earning_product = self.product.get_product_earning(self.user)
        self.assertIsNone(earning_product)

    def test_product_details_user_is_not_publisher_no_commission(self):
        is_logged_in = self.client.login(username='normal_user', password='normal')
        self.assertTrue(is_logged_in)

        self.user.is_partner = True
        self.user.save()

        get_model('dashboard', 'StoreCommission').objects.create(vendor=self.vendor,commission="6/10/0")

        earning_product = self.product.get_product_earning(self.user)
        self.assertIsNone(earning_product)

    def test_extracting_suffix(self):
        from apparelrow.apparel.views import extract_domain_with_suffix
        domain = "https://account.manning.com/support/index?someparameter=1"
        self.assertEquals("manning.com",extract_domain_with_suffix(domain))
        domain = "https://account.manning.co.uk/support/index?someparameter=1"
        self.assertEquals("manning.co.uk",extract_domain_with_suffix(domain))


class TestProfileLikes(TestCase):
    def setUp(self):
        # Group is subscriber
        owner_user = User.objects.create(name="Owner Test", username="owner", slug="owner", is_active=True,
                                         email="owner@test.com", is_subscriber=True)
        group = Group.objects.create(name="Group Test", owner=owner_user)

        # User belongs to a partner group
        user_test = User.objects.create(name="Blogger Test", username="usertest", slug="user_test",
                                        email="user@test.com", partner_group=group, is_active=True,
                                        owner_network=owner_user)
        user_test.set_password("1234qwer")
        user_test.save()

        # Group is not subscriber
        owner_user_ns = User.objects.create(name="Owner NS Test", username="ownerns", slug="ownerns", is_active=True, email="ownerns@test.com")
        group_ns = Group.objects.create(name="Group NS Test", owner=owner_user_ns)

        # User belongs to a partner group
        user_test_ns = User.objects.create(name="Blogger NS Test", username="usertestns", slug="user_test_ns",
                                        email="userns@test.com", partner_group=group_ns, is_active=True,
                                        owner_network=owner_user_ns, is_subscriber=True)
        user_test_ns.set_password("1234qwer")
        user_test_ns.save()

        # User doesn't belong to a partner group
        no_partner_user = User.objects.create(name="No Partner Test", username="nopartneruser", slug="no_partner_user",
                                        email="no_partner_user@test.com", is_active=True)
        no_partner_user.set_password("1234qwer")
        no_partner_user.save()

    def test_product_like_group_partner_group_is_subscriber(self):
        """
            Tests if an user likes a product and belongs to a partner group and it's not the owner, also the group has
            set is_subscriber to True, which means the owner of that partner group will automatically like that
            product too
        """
        product = Product.objects.create(slug="product_test", static_brand="testbrand", sku="testsku")
        owner_user = User.objects.get(email="owner@test.com")

        user = User.objects.get(email="user@test.com")
        self.assertTrue(user.is_active)

        c = Client()

        login = c.login(username="usertest", password="1234qwer")
        self.assertTrue(login)

        count_b = ProductLike.objects.all().count()

        response = c.post(reverse('product-action', kwargs={'pk': product.id,'action':'like'}))
        self.assertEqual(response.status_code, 200)

        count_a = ProductLike.objects.all().count()

        # Two ProductLike objects should be generated
        self.assertEqual(count_a-count_b, 2)

        user_like = ProductLike.objects.filter(user=user, product=product)
        self.assertEqual(len(user_like), 1)
        self.assertTrue(user_like[0].active)

        owner_like = ProductLike.objects.filter(user=owner_user, product=product)
        self.assertEqual(len(owner_like), 1)
        self.assertTrue(owner_like[0].active)

    def test_product_unlike_group_partner_group_is_subscriber(self):
        """
            Tests if an user unlikes a product and belongs to a partner group and it's not the owner, also the group has
            set is_subscriber to True, which means the owner of that partner group will automatically unlike that
            product
        """
        product = Product.objects.create(slug="product_test", static_brand="testbrand", sku="testsku")
        owner_user = User.objects.get(email="owner@test.com")

        c = Client()

        user = User.objects.get(email="user@test.com")
        login = c.login(username="usertest", password="1234qwer")
        self.assertTrue(login)

        response = c.post(reverse('product-action', kwargs={'pk': product.id,'action':'unlike'}))
        self.assertEqual(response.status_code, 200)

        user_like = ProductLike.objects.filter(user=user, product=product)
        self.assertEqual(len(user_like), 1)
        self.assertFalse(user_like[0].active)

        owner_like = ProductLike.objects.filter(user=owner_user, product=product)
        self.assertEqual(len(owner_like), 1)
        self.assertFalse(owner_like[0].active)

    def test_product_like_no_group_partner(self):
        """
            Tests if an user likes a product and doesn't belong to a partner group and it's not the owner,
            the owner of that partner group will automatically like the product also
        """
        product = Product.objects.create(slug="product_test", static_brand="testbrand", sku="testsku")
        owner_user = User.objects.get(email="owner@test.com")

        user = User.objects.get(email="no_partner_user@test.com")
        self.assertTrue(user.is_active)

        c = Client()

        login = c.login(username="nopartneruser", password="1234qwer")
        self.assertTrue(login)

        count_b = ProductLike.objects.all().count()

        response = c.post(reverse('product-action', kwargs={'pk': product.id,'action':'like'}))
        self.assertEqual(response.status_code, 200)

        count_a = ProductLike.objects.all().count()

        # One ProductLike objects should be generated
        self.assertEqual(count_a-count_b, 1)

        user_like = ProductLike.objects.filter(user=user, product=product)
        self.assertEqual(len(user_like), 1)
        self.assertTrue(user_like[0].active)

        owner_like = ProductLike.objects.filter(user=owner_user, product=product)
        self.assertEqual(len(owner_like), 0)

    def test_product_like_group_partner_group_is_not_subscriber(self):
        """
            Tests if an user likes a product and belongs to a partner group and it's not the owner, also the group has
            set is_subscriber to False, which means the owner of that partner group won't automatically like the product
        """
        product = Product.objects.create(slug="product_test", static_brand="testbrand", sku="testsku")
        owner_user = User.objects.get(email="ownerns@test.com")

        user = User.objects.get(email="userns@test.com")
        self.assertTrue(user.is_active)

        c = Client()

        login = c.login(username="usertestns", password="1234qwer")
        self.assertTrue(login)

        count_b = ProductLike.objects.all().count()

        response = c.post(reverse('product-action', kwargs={'pk': product.id,'action':'like'}))
        self.assertEqual(response.status_code, 200)

        count_a = ProductLike.objects.all().count()

        # One ProductLike objects should be generated
        self.assertEqual(count_a-count_b, 1)

        user_like = ProductLike.objects.filter(user=user, product=product)
        self.assertEqual(len(user_like), 1)
        self.assertTrue(user_like[0].active)

        owner_like = ProductLike.objects.filter(user=owner_user, product=product)
        self.assertEqual(len(owner_like), 0)


class TestEmbeddingShops(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        #self.product1 = get_model('apparel', 'Product').objects.create()
        #self.product2 = get_model('apparel', 'Product').objects.create()

    def test_create_shop(self):
        is_logged_in = self.client.login(username='normal_user', password='normal')
        self.assertTrue(is_logged_in)
        self.assertEquals(Shop.objects.count(),0)
        self.assertEquals(ShopEmbed.objects.count(),0)
        #self.assertTrue( get_model('apparel', 'Product').objects.all().count() > 0 )
        data = {"published":False,"title":"asdfasdfa","show_liked":False,"components":[{"product":
        {"image_medium":"/media/cache/d977424fd3a3f97af91e56dc026d186a/fa/fa194102addee4a2554214ad037b90c90c617d52.jpg",
        "image_look":"/media/cache/247c1e41bf054ef49085a6f7a24e77a7/fa/fa194102addee4a2554214ad037b90c90c617d52.jpg",
        "currency":"USD","url":"http://localhost:8000/en/redirect/2864777/Ext-Site/0/","product_name":"Gabrielle top",
        "price":"20","image_small":"/media/cache/373f13670c71403a969502b410483b9e/fa/fa194102addee4a2554214ad037b90c90c617d52.jpg",
        "brand_name":"365","availability":True,"discount":False,"id":"","discount_price":"0","slug":"365-gabrielle-top"}},
        {"product":{"image_medium":"/media/cache/846da68b1374f6120adafa5d8b4688dc/34/34a50db94764ee6a07a4ab7ca00e664651fa6e8b.jpg",
        "image_look":"/media/cache/22e4c36ad8a551979c13dd51babb25a5/34/34a50db94764ee6a07a4ab7ca00e664651fa6e8b.jpg",
        "currency":"USD","url":"http://localhost:8000/en/redirect/2864747/Ext-Site/0/","product_name":"Deep Blue Pinpoint",
        "price":"117","image_small":"/media/cache/c7740bf7554c65c31b1cde9aa18029ec/34/34a50db94764ee6a07a4ab7ca00e664651fa6e8b.jpg",
        "brand_name":"Shirtonomy","availability":True,"discount":False,"id":"",
        "discount_price":"0","slug":"shirtonomy-deep-blue-pinpoint"}}]}

        self.product1 = get_model('apparel', 'Product').objects.create(**{"sku":1})
        self.product2 = get_model('apparel', 'Product').objects.create(**{"sku":2})
        self.assertTrue(get_model('apparel', 'Product').objects.count() > 0)
        self.assertTrue(self.product1.id)
        self.assertTrue(self.product2.id)
        data.get("components")[0]["product"]["id"] = self.product1.id
        data.get("components")[1]["product"]["id"] = self.product2.id
        self.assertTrue(data.get("components")[0]["product"]["id"])
        self.assertTrue(data.get("components")[1]["product"]["id"])
        print "Trying to call url %s " % reverse('create_shop')
        response = self.client.post(reverse('create_shop'),data=json.dumps(data),content_type='application/json',)
        print response.status_code
        self.assertTrue(response.status_code in [201])
        content = json.loads(response.content)
        self.assertEqual(content.get("published"), True)
        self.assertEqual(content.get("user"), "normal_user")
        self.assertEqual(content.get("url"), "/shop/create/api/1")
        self.assertEqual(content.get("id"), 1)
        self.assertEquals(Shop.objects.count(),1)
        response = self.client.get(content.get("url"),follow=True)
        content = json.loads(response.content)
        self.assertEqual(content.get("published"), True)
        self.assertEqual(content.get("user"), "normal_user")
        self.assertEqual(content.get("url"), "/shop/create/api/1")
        self.assertEqual(content.get("id"), 1)
        print "Calling shop widget %s" % reverse('shop-widget',args=(content.get("id"),))
        response = self.client.post(reverse('shop-widget',args=(content.get("id"),)))
        print response.status_code
        self.assertTrue(response.status_code in [200])
        url = reverse('embed-shop',args=(content.get("id"),))
        print "Calling %s to be embedded into the cache." % url
        self.client.get(url)
        from django.core.cache import get_cache
        cache = get_cache('nginx')
        nginx_key = reverse('embed-shop', args=[1])
        print "Checking cache key for: %s" % nginx_key
        self.assertIsNotNone(cache.get(nginx_key,None))


class TestShortLinks(TestCase):
    def setUp(self):
        self.vendor = get_model('apparel', 'Vendor').objects.create(name='My Store 12')
        self.group = get_model('dashboard', 'Group').objects.create(name='mygroup')

        self.user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        self.user.partner_group = self.group
        self.user.save()

    def test_store_link(self):
        template = "http://www.anrdoezrs.net/links/4125005/type/dlg/sid/{sid}/http://www.nastygal.com/"
        store_link = get_model('apparel', 'ShortStoreLink').objects.create(vendor=self.vendor, template=template)

        stats_count = get_model('statistics', 'ProductStat').objects.count()
        store_link_str = store_link.link()
        referer = reverse('store-short-link-userid', kwargs={'short_link': store_link_str, 'user_id': self.user.id})

        # Make the call directly to product-track, since the client doesn't follow the redirect made
        # from template in jQuery
        url = reverse('product-track', kwargs={'pk': 0, 'page': 'Ext-Store', 'sid': self.user.id})
        print "requesting url: %s" % url
        response = self.client.post(url, {'referer': referer}, **{'HTTP_REFERER': referer})
        self.assertEqual(response.status_code, 200)

        # A ProductStat were created
        self.assertEqual(get_model('statistics', 'ProductStat').objects.count(), stats_count + 1)

        product_stat = get_model('statistics', 'ProductStat').objects.latest("created")
        self.assertEqual(product_stat.page, 'Ext-Store')
        self.assertEqual(product_stat.vendor, self.vendor.name)
        self.assertEqual(product_stat.user_id, self.user.id)
        self.assertEqual(product_stat.action, 'StoreLinkClick')

    def test_store_link_invalid(self):
        stats_count = get_model('statistics', 'ProductStat').objects.count()
        url = reverse('store-short-link-userid', kwargs={'short_link': 'random', 'user_id': self.user.id})

        response = self.client.post(url, follow=False)
        self.assertEqual(response.status_code, 404)

        # No ProductStat were created
        self.assertEqual(get_model('statistics', 'ProductStat').objects.count(), stats_count)

