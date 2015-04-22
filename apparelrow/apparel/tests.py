import json

from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.test.utils import override_settings
from decimal import Decimal
from django.conf import settings

from django.core.urlresolvers import reverse
from django.test import TestCase
from apparelrow.apparel.models import Product, ProductLike
from apparelrow.profile.models import User
from apparelrow.dashboard.models import Group
from django.test import Client



""" CHROME EXTENSION """
@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestChromeExtension(TestCase):

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

        self.assertEqual(json_content['profile'], u'http://testserver/en/profile/normal_user/')
        self.assertEqual(json_content['authenticated'], True)

    def test_product_lookup_not_logged_in(self):
        response = self.client.get('/backend/product/lookup/?key=not_found_url&domain=example.com')
        self.assertEqual(response.status_code, 404)

    def test_product_lookup_not_found(self):
        self._login()

        response = self.client.get('/backend/product/lookup/?key=not_found_url&domain=example.com')
        self.assertEqual(response.status_code, 404)

    def test_product_lookup_by_domain(self):
        self._login()

        vendor = get_model('apparel', 'Vendor').objects.create(name='Vendor')
        get_model('apparel', 'DomainDeepLinking').objects.create(
            vendor=vendor,
            domain='example.com/se',
            template='http://example.com/my-template'
        )

        response = self.client.get('/backend/product/lookup/?key=example.com/se/shoes?product=123&domain=example.com/se/shoes')
        json_content = json.loads(response.content)

        self.assertEqual(json_content['product_pk'], None)
        self.assertEqual(json_content['product_link'], None)
        self.assertEqual(json_content['product_short_link'], 'http://testserver/en/pd/4C92/')
        self.assertEqual(json_content['product_liked'], False)

    def test_product_lookup_by_url(self):
        self._login()

        vendor = get_model('apparel', 'Vendor').objects.create(name='Vendor')
        category = get_model('apparel', 'Category').objects.create(name='Category')
        manufacturer = get_model('apparel', 'Brand').objects.create(name='Brand')
        product = get_model('apparel', 'Product').objects.create(
            product_name='Product',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True
        )
        theimp_vendor = get_model('theimp', 'Vendor').objects.create(name='Vendor', vendor=vendor)
        theimp_product = get_model('theimp', 'Product').objects.create(
            key='http://example.com/example',
            vendor=theimp_vendor,
            json='{"site_product": 1}'
        )

        response = self.client.get('/backend/product/lookup/?key=http://example.com/example&domain=example.com')
        self.assertEqual(response.status_code, 200)
        json_content = json.loads(response.content)

        self.assertEqual(json_content['product_pk'], 1)
        self.assertEqual(json_content['product_link'], 'http://testserver/products/product/')
        self.assertEqual(json_content['product_short_link'], 'http://testserver/en/p/4C92/')
        self.assertEqual(json_content['product_liked'], False)


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

