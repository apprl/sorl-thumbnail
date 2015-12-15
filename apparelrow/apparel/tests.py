# -*- coding: utf-8 -*-
import json
from pysolr import Solr
from sorl.thumbnail import get_thumbnail
from apparelrow.apparel.search import product_save, get_product_document
from apparelrow.apparel.views import get_earning_cut, get_vendor_cost_per_click, get_product_earning
from apparelrow.apparel.views import product_lookup_asos_nelly, product_lookup_by_solr, embed_wildcard_solr_query, \
    extract_asos_nelly_product_url
from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from decimal import Decimal
from django.conf import settings
from apparelrow.apparel.models import Shop, ShopEmbed

from django.core.urlresolvers import reverse
from django.utils.translation import activate
from django.test import TestCase
from apparelrow.apparel.models import Product, ProductLike
from apparelrow.profile.models import User
from apparelrow.dashboard.models import Group
from django.test import Client
from factories import *

""" CHROME EXTENSION """
@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestChromeExtension(TestCase):
    django_image_file = None

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
        from PIL import Image
        from StringIO import StringIO

        from django.core.files.base import ContentFile

        image_file = StringIO()
        image = Image.new('RGBA', size=(50,50), color=(256,0,0))
        image.save(image_file, 'png')
        image_file.seek(0)

        self.django_image_file = ContentFile(image_file.read(), 'test.png')

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
        import urllib
        response = self.client.get('/backend/product/lookup/?key=not_found_url&domain=weird.com')
        self.assertEqual(response.status_code, 404)

    def test_encode_and_lookup_utf_urls(self):
        self._login()
        url = '/backend/product/lookup/?key=http%3A%2F%2Fnelly.com%2Fse%2Fkl%25C3%25A4der-f%25C3%25B6r-kvinnor%2Fkl%25C3%25A4der%2Ffestkl%25C3%25A4nningar%2F%23hits%3D144%26sort%3DLastArrival%26priceTo%3D299&domain=nelly.com%2Fse%2Fkl%25C3%25A4der-f%25C3%25B6r-kvinnor%2Fkl%25C3%25A4der%2Ffestkl%25C3%25A4nningar%2F&is_product=0'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

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
        self.assertTrue(json_content['product_short_link'].startswith('http://testserver/pd/4C9'))
        self.assertEqual(json_content['product_liked'], False)

    def test_product_lookup_by_url(self):
        self._login()
        product_key = 'http://example.com/example?someproduct=12345'
        product_id = product_lookup_by_solr(None, product_key)
        if product_id:
            print "Found already existing product in SOLR database, removing."
            connection = Solr(settings.SOLR_URL)
            product_solr_id = "apparel.product.%s" % product_id
            connection.delete(id=product_solr_id, commit=True, waitFlush=True)
            print "%s has been removed from index." % product_solr_id
        vendor = get_model('apparel', 'Vendor').objects.create(name='Vendor')
        category = get_model('apparel', 'Category').objects.create(name='Category')
        manufacturer = get_model('apparel', 'Brand').objects.create(name='Brand')
        product = ProductFactory.create(
            product_name='Product',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            published=True,
            product_key=product_key,
            availability=True,
            product_image=self.django_image_file
        )
        self.assertIsNotNone(product.product_image)
        self.assertIsNotNone(get_thumbnail(product.product_image, '112x145', crop=False, format='PNG', transparent=True).url)
        vendorproduct = VendorProductFactory.create(vendor=vendor, product=product, availability=True)
        del product.default_vendor
        product_save(product, commit=True)
        self.assertIsNotNone(vendorproduct.id)
        self.assertIsNotNone(product.id)
        self.assertIsNotNone(product.default_vendor)
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

        self.assertIsNotNone(json_content['product_pk'])
        self.assertEqual(int(json_content['product_pk']), product.id)
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

    def test_extract_asos_nelly_product_url(self):
        asos_url = "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2108486&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlw&istBid=t&channelref=affiliate"
        key, vendor_id = extract_asos_nelly_product_url(asos_url)
        self.assertEquals(key, "/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2108486")

        url_cause_exception = "https://www.asos.com/women/"
        key, vendor_id = extract_asos_nelly_product_url(url_cause_exception)
        self.assertIsNone(key)
        self.assertIsNone(vendor_id)

        asos_url_2 = "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2109266&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlq&istBid=t&channelref=affiliate"
        key, vendor_id = extract_asos_nelly_product_url(asos_url_2)
        self.assertEquals(key, "/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2109266")

        asos_url_3 = "http://www.asos.com/ASOS/ASOS-Mix-and-Match-Halter-Leopard-Print-Bikini-Top/Prod/pgeproduct.aspx?iid=2125546&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=witimippa&istBid=t&channelref=affiliate"
        key, vendor_id = extract_asos_nelly_product_url(asos_url_3)
        self.assertEquals(key, "/ASOS/ASOS-Mix-and-Match-Halter-Leopard-Print-Bikini-Top/Prod/pgeproduct.aspx?iid=2125546")

        luis_avairoma_url_4 = "http://www.luisaviaroma.com/index.aspx#ItemSrv.ashx|SeasonId=60I&CollectionId=CD1&ItemId=14&SeasonMemoCode=actual&GenderMemoCode=women&CategoryId=&SubLineId=clothing"
        key, vendor_id = extract_asos_nelly_product_url(luis_avairoma_url_4)
        self.assertEquals(key, "60I-CD1014")

        luis_avairoma_url_5 = "http://www.luisaviaroma.com/adidas+originals+by+mary+katrantzou/women/skirts/60I-CD1013/lang_EN"
        key, vendor_id = extract_asos_nelly_product_url(luis_avairoma_url_5)
        self.assertEquals(key, luis_avairoma_url_5)

        nelly_url_6 = "http://nelly.com/se/kl\u00e4der-f\u00f6r-kvinnor/kl\u00e4der/festkl\u00e4nningar/nly-trend-917/scuba-wrap-dress-917910-29/"
        key, vendor_id = extract_asos_nelly_product_url(nelly_url_6, True)
        self.assertEquals(key, "/scuba-wrap-dress-917910-29/")

        nelly_url_7 = "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/kl%C3%A4der/festkl%C3%A4nningar/nly-trend-917/scuba-wrap-dress-917910-29/"
        key, vendor_id = extract_asos_nelly_product_url(nelly_url_7, True)
        self.assertEquals(key, "/scuba-wrap-dress-917910-29/")

        nelly_url_8 = "http://nelly.com/se/somecategory/somesubcategory/otherparam/closet-1153/quilt-effect-dress-601764-2350/"
        key, vendor_id = extract_asos_nelly_product_url(nelly_url_8, True)
        self.assertEquals(key, "/quilt-effect-dress-601764-2350/")

        nelly_url_9 = "http://nelly.com/se/skor-kvinna/skor/vardagsskor/nike-1013/wmns-nike-air-max-thea-118540-54/"
        key, vendor_id = extract_asos_nelly_product_url(nelly_url_9, True)
        self.assertEquals(key, "/wmns-nike-air-max-thea-118540-54/")


    def test_product_asos_nelly_luisaviaroma(self):
        #1st ASOS product
        # original
        # after click
        # manual search
        # from "last viewed"
        original_keys = ["http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2108486&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlw&istBid=t&channelref=affiliate",
                        "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2108486&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlw&istBid=t&channelref=affiliate&r=2",
                        #"http://www.asos.com/asos/asos-vest-with-extreme-racer-back/prod/pgeproduct.aspx?iid=2108486&clr=Grey&SearchQuery=Vest+With+Extreme+Racer+Back&pgesize=36&pge=1&totalstyles=101&gridsize=3&gridrow=2&gridcolumn=3",
                        "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2108486&CTARef=Recently%20Viewed"]
        template_key = "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2108486&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlw&istBid=t&channelref=affiliate"
        _cleanout_products(original_keys)
        product_id = _send_product_to_solr(product_key=template_key)

        for original_key in original_keys:
            self.assertEqual(product_lookup_asos_nelly(original_key), product_id)

        #2nd ASOS product
        #original
        #after click
        # manual search, removed
        #key = "http://www.asos.com/asos/asos-vest-with-extreme-racer-back/prod/pgeproduct.aspx?iid=2109266&clr=White&SearchQuery=Vest+With+Extreme+Racer+Back&pgesize=36&pge=1&totalstyles=100&gridsize=3&gridrow=2&gridcolumn=2"
        original_keys = [ "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2109266&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlq&istBid=t&channelref=affiliate",
                          "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2109266&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlq&istBid=t&channelref=affiliate"]
        template_key =    "http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2109266&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlq&istBid=t&channelref=affiliate"
        _cleanout_products(original_keys)
        product_id = _send_product_to_solr(product_key=template_key)
        for original_key in original_keys:
            self.assertEqual(product_lookup_asos_nelly(original_key), product_id)


        #3rd ASOS product
        #original
        #after click
        #manual search
        #key = "http://www.asos.com/asos/asos-mix-and-match-halter-leopard-print-bikini-top/prod/pgeproduct.aspx?iid=2125546&clr=Leopardprint&SearchQuery=Mix+and+Match+Halter+Leopard+Print+Bikini+Top&SearchRedirect=true"
        #self.assertEqual(product_lookup_asos_nelly(key), product_id)
        original_keys = ["http://www.asos.com/ASOS/ASOS-Mix-and-Match-Halter-Leopard-Print-Bikini-Top/Prod/pgeproduct.aspx?iid=2125546&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=witimippa&istBid=t&channelref=affiliate",
                         "http://www.asos.com/ASOS/ASOS-Mix-and-Match-Halter-Leopard-Print-Bikini-Top/Prod/pgeproduct.aspx?iid=2125546&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=witimippa&istBid=t&channelref=affiliate"
                         ]
        template_key = "http://www.asos.com/ASOS/ASOS-Mix-and-Match-Halter-Leopard-Print-Bikini-Top/Prod/pgeproduct.aspx?iid=2125546&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=witimippa&istBid=t&channelref=affiliate"
        _cleanout_products(original_keys)
        product_id = _send_product_to_solr(product_key=template_key)
        for original_key in original_keys:
            self.assertEqual(product_lookup_asos_nelly(original_key), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key), 883416)

        #1st Luisaviaroma product
        #original
        #after click
        #manual search

        original_keys = ["http://www.luisaviaroma.com/adidas+originals+by+mary+katrantzou/women/t-shirts/60I-CD1014/lang_EN",
                         "http://www.luisaviaroma.com/index.aspx#ItemSrv.ashx|SeasonId=60I&CollectionId=CD1&ItemId=14&SeasonMemoCode=actual&GenderMemoCode=women&CategoryId=&SubLineId=clothing",
                         "http://www.luisaviaroma.com/index.aspx?#ItemSrv.ashx|SeasonId=60I&CollectionId=CD1&ItemId=14&VendorColorId=TTYzMDU30&SeasonMemoCode=actual&GenderMemoCode=women&CategoryId=&SubLineMemoCode=",
                         ]
        template_key = "http://www.luisaviaroma.com/adidas+originals+by+mary+katrantzou/women/t-shirts/60I-CD1014/lang_EN"
        _cleanout_products(original_keys)
        product_id = _send_product_to_solr(product_key=template_key)
        for original_key in original_keys:
            self.assertEqual(product_lookup_asos_nelly(original_key), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key), 883598)

        #self.assertEqual(product_lookup_asos_nelly(key), 883598)

        #2nd Luisaviaroma product
        #original
        #after click
        #manual search
        original_keys = ["http://www.luisaviaroma.com/adidas+originals+by+mary+katrantzou/women/skirts/60I-CD1013/lang_EN",
                         "http://www.luisaviaroma.com/index.aspx#ItemSrv.ashx|SeasonId=60I&CollectionId=CD1&ItemId=13&SeasonMemoCode=actual&GenderMemoCode=women&CategoryId=&SubLineId=clothing",
                         "http://www.luisaviaroma.com/index.aspx?#ItemSrv.ashx|SeasonId=60I&CollectionId=CD1&ItemId=13&VendorColorId=TTYzMTAy0&SeasonMemoCode=actual&GenderMemoCode=women&CategoryId=&SubLineMemoCode=",
                         ]

        template_key = "http://www.luisaviaroma.com/adidas+originals+by+mary+katrantzou/women/skirts/60I-CD1013/lang_EN"
        _cleanout_products(original_keys)
        product_id = _send_product_to_solr(product_key=template_key)
        for original_key in original_keys:
            self.assertEqual(product_lookup_asos_nelly(original_key), product_id)

        #self.assertEqual(product_lookup_asos_nelly(key), 883602)

        #1st Nelly product
        #original
        #after click
        #manual search
        original_keys = ["http://nelly.com/se/kl\u00e4der-f\u00f6r-kvinnor/kl\u00e4der/festkl\u00e4nningar/nly-trend-917/scuba-wrap-dress-917910-29/",
                         "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/kl%C3%A4der/festkl%C3%A4nningar/nly-trend-917/scuba-wrap-dress-917910-29/"
                         "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/kl%C3%A4der/festkl%C3%A4nningar/nly-trend-917/scuba-wrap-dress-917910-29/"

                        ]
        template_key = "http://nelly.com/se/kl\u00e4der-f\u00f6r-kvinnor/kl\u00e4der/festkl\u00e4nningar/nly-trend-917/scuba-wrap-dress-917910-29/"
        _cleanout_products(original_keys)
        product_id = _send_product_to_solr(product_key=template_key)
        for original_key in original_keys:
            self.assertEqual(product_lookup_asos_nelly(original_key, True), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key, True), 883607)
        #product_id = _send_product_to_solr(product_key=key)
        #self.assertEqual(product_lookup_asos_nelly(key, True), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key, True), 883607)
        #product_id = _send_product_to_solr(product_key=key)
        #self.assertEqual(product_lookup_asos_nelly(key, True), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key, True), 883607)

        #2nd Nelly product
        #original
        #after click
        #manual search
        #made up category
        original_keys = ["http://nelly.com/se/kl\u00e4der-f\u00f6r-kvinnor/kl\u00e4der/festkl\u00e4nningar/closet-1153/quilt-effect-dress-601764-2350/",
                         "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/kl%C3%A4der/festkl%C3%A4nningar/closet-1153/quilt-effect-dress-601764-2350/",
                         "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/kl%C3%A4der/festkl%C3%A4nningar/closet-1153/quilt-effect-dress-601764-2350/",
                         "http://nelly.com/se/somecategory/somesubcategory/otherparam/closet-1153/quilt-effect-dress-601764-2350/"
                        ]
        template_key = "http://nelly.com/se/kl\u00e4der-f\u00f6r-kvinnor/kl\u00e4der/festkl\u00e4nningar/closet-1153/quilt-effect-dress-601764-2350/"
        _cleanout_products(original_keys)
        product_id = _send_product_to_solr(product_key=template_key)
        for original_key in original_keys:
            self.assertEqual(product_lookup_asos_nelly(original_key, True), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key, True), 883603)
        #product_id = _send_product_to_solr(product_key=key)
        #self.assertEqual(product_lookup_asos_nelly(key, True), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key, True), 883603)
        #product_id = _send_product_to_solr(product_key=key)
        #self.assertEqual(product_lookup_asos_nelly(key, True), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key, True), 883603)
        #product_id = _send_product_to_solr(product_key=key)
        #self.assertEqual(product_lookup_asos_nelly(key, True), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key, True), 883603)

        #3rd Nelly product from pivotaltracker story
        #original
        #other
        original_keys = ["http://nelly.com/se/skor-kvinna/skor/vardagsskor/nike-1013/wmns-nike-air-max-thea-118540-54/",
                         "http://nelly.com/se/kl%C3%A4der-f%C3%B6r-kvinnor/skor/vardagsskor/nike-1013/wmns-nike-air-max-thea-118540-54"
                         ]
        template_key = "http://nelly.com/se/skor-kvinna/skor/vardagsskor/nike-1013/wmns-nike-air-max-thea-118540-54/"
        _cleanout_products(original_keys)
        product_id = _send_product_to_solr(product_key=template_key)
        for original_key in original_keys:
            self.assertEqual(product_lookup_asos_nelly(original_key, True), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key, True), 883604)
        #product_id = _send_product_to_solr(product_key=key)
        #self.assertEqual(product_lookup_asos_nelly(key, True), product_id)
        #self.assertEqual(product_lookup_asos_nelly(key, True), 883604)

    def test_embed_wildcard_solr_query(self):
        test_strings = [
                    ("product_key:asbasf://asdfkh+asdf","product_key:*asbasf://asdfkh+asdf*"),
                    ("product_key:/wmns\-nike\-air\-max\-thea\-118540\-54/","product_key:*/wmns\-nike\-air\-max\-thea\-118540\-54/*"),
                    ("id:apparel.product.883624","id:*apparel.product.883624*"),
                    ("pro:asb","pro:*asb*"),
                        ]
        for i1,i2 in test_strings:
            self.assertEquals(i2,embed_wildcard_solr_query(i1))


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

@override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="SE")
class TestUtils(TestCase):

    def setUp(self):
        activate('sv')
        vendor_success = VendorFactory.create(name="Vendor Success", is_cpc=True, is_cpo=False)
        get_model('dashboard', 'ClickCost').objects.create(vendor=vendor_success, amount=1.00, currency="EUR")

        VendorFactory.create(name="Vendor Fail", is_cpc=True, is_cpo=False)

        self.group = get_model('dashboard', 'Group').objects.create(name='mygroup')
        self.user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        self.user.partner_group = self.group
        self.user.is_partner = True
        self.user.location = 'SE'
        self.user.save()

        self.django_image_file = _create_dummy_image()
        self.category = CategoryFactory.create()
        self.manufacturer = BrandFactory.create()
        self.product_cpc = ProductFactory.create(
            product_name='Product CPC',
            category=self.category,
            manufacturer=self.manufacturer,
            gender='M',
            published=True,
            availability=True,
            product_image=self.django_image_file
        )
        vendorproduct = VendorProductFactory.create(vendor=vendor_success, product=self.product_cpc, availability=True)
        del self.product_cpc.default_vendor
        product_save(self.product_cpc, commit=True)
        self.assertIsNotNone(vendorproduct.id)
        self.assertIsNotNone(self.product_cpc.default_vendor)

        get_model('dashboard', 'Cut').objects.create(group=self.group, vendor=vendor_success,
                                                     cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT,
                                                     referral_cut=settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT)

    def test_get_vendor_cost_per_click(self):
        """ Test function that returns cost per click when is a valid Vendor with valid Cost per click
            object associated
        """
        vendor_success = get_model('apparel', 'Vendor').objects.get(name="Vendor Success")
        cost_per_click = get_vendor_cost_per_click(vendor_success)

        self.assertIsNotNone(cost_per_click)
        self.assertEqual(cost_per_click.amount, 1)
        self.assertEqual(cost_per_click.currency, "EUR")
        self.assertEqual(cost_per_click.vendor, vendor_success)

    def test_get_vendor_cost_per_click_is_none(self):
        """ Test function that returns cost per click when Vendor has not related Cost per Click object created.
        """
        vendor_fail = get_model('apparel', 'Vendor').objects.get(name="Vendor Fail")
        cost_per_click = get_vendor_cost_per_click(vendor_fail)

        self.assertIsNone(cost_per_click)

    def test_product_earning_is_cpc(self):
        """ Test functions that returns earning cut and product earning for a CPC vendor with Cost per Click
        """
        self.assertIsNotNone(self.product_cpc.default_vendor)

        # Test get earning cut
        earning_cut = get_earning_cut(self.user, self.product_cpc.default_vendor, self.product_cpc)
        self.assertEqual(earning_cut, Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

        click_cost = get_model('dashboard', 'ClickCost').objects.get(vendor=self.product_cpc.default_vendor.vendor)
        self.assertIsNotNone(click_cost)
        # Test product earning
        product_earning = get_product_earning(self.user, self.product_cpc.default_vendor, self.product_cpc)
        self.assertEqual("%.2f" % product_earning, "%.2f" % (click_cost.amount * earning_cut))

    def test_product_earning_is_cpo(self):
        """ Test functions that returns earning cut and product earning for a CPO vendor
        """
        vendor_cpo = VendorFactory.create(name="Vendor CPO")
        store = StoreFactory.create(vendor=vendor_cpo, commission_percentage='0.2')
        product_cpo = ProductFactory.create(
            product_name='Product CPO',
            category=self.category,
            manufacturer=self.manufacturer,
            gender='M',
            published=True,
            availability=True,
            product_image=self.django_image_file
        )
        vendorproduct = VendorProductFactory.create(vendor=vendor_cpo, product=product_cpo, availability=True)
        del product_cpo.default_vendor
        product_save(product_cpo, commit=True)
        self.assertIsNotNone(vendorproduct.id)
        self.assertIsNotNone(product_cpo.default_vendor)

        get_model('dashboard', 'Cut').objects.create(group=self.group, vendor=vendor_cpo,
                                                     cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT,
                                                     referral_cut=settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT)
        earning_cut = get_earning_cut(self.user, product_cpo.default_vendor, product_cpo)
        self.assertEqual("%.2f" % earning_cut, "%.2f" %
                               (Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT) * Decimal(store.commission_percentage)))

        product_earning = get_product_earning(self.user, product_cpo.default_vendor, product_cpo)
        self.assertEqual("%.2f" % product_earning, "%.2f" % (product_cpo.default_vendor.locale_price * earning_cut))

    def test_product_earning_no_default_vendor(self):
        """ Test functions that returns earning cut and product earning when Vendor is None
        """
        product_no_vendor = ProductFactory.create(
            product_name='Product No Vendor',
            category=self.category,
            manufacturer=self.manufacturer,
            gender='M',
            published=True,
            availability=True,
            product_image=self.django_image_file
        )
        earning_cut = get_earning_cut(self.user, product_no_vendor.default_vendor, product_no_vendor)
        self.assertIsNone(earning_cut)

        product_earning = get_product_earning(self.user, product_no_vendor.default_vendor, product_no_vendor)
        self.assertIsNone(product_earning)

def _send_product_to_solr(product_key):

    django_image_file = _create_dummy_image()
    _cleanout_product(product_key)
    vendor = VendorFactory.create()
    category = CategoryFactory.create()
    manufacturer = BrandFactory.create()
    product = ProductFactory.create(
        product_name='Product',
        category=category,
        manufacturer=manufacturer,
        gender='M',
        published=True,
        product_key=product_key,
        availability=True,
        product_image=django_image_file
    )
    assert(product.product_image)
    assert(get_thumbnail(product.product_image, '112x145', crop=False, format='PNG', transparent=True).url)
    vendorproduct = VendorProductFactory.create(vendor=vendor, product=product, availability=True)
    del product.default_vendor
    product_save(product, commit=True)
    return product.id

def _cleanout_products(product_keys):
    for product_key in product_keys:
        _cleanout_product(product_key)

def _cleanout_product(product_key):
    product_id = product_lookup_by_solr(None, product_key)
    if product_id:
        print "Found already existing product in SOLR database, removing."
        connection = Solr(settings.SOLR_URL)
        product_solr_id = "apparel.product.%s" % product_id
        connection.delete(id=product_solr_id, commit=True, waitFlush=True)
        print "%s has been removed from index." % product_solr_id
    else:
        print "No previous products found"

def _create_dummy_image():
    from PIL import Image
    from StringIO import StringIO
    from django.core.files.base import ContentFile
    image_file = StringIO()
    image = Image.new('RGBA', size=(50,50), color=(256,0,0))
    image.save(image_file, 'png')
    image_file.seek(0)

    return ContentFile(image_file.read(), 'test.png')