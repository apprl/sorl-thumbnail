import json

from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.test import TestCase
from django.test.utils import override_settings
from decimal import Decimal
from django.conf import settings
from apparelrow.apparel.models import Shop, ShopEmbed
from apparelrow.dashboard.tests import reverse


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
        response = self.client.post(reverse('create_shop')[3:],data=json.dumps(data),content_type='application/json',)
        self.assertEqual(response.status_code, 201)
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
