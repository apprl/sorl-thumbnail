"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import decimal
import urllib
import unittest

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model

from localeurl.utils import locale_url

from advertiser.views import get_cookie_name
from advertiser.models import Transaction, Store, StoreHistory, Cookie
from django.core.cache import cache
from django.conf import settings


def reverse_locale(*args, **kwargs):
    return locale_url(reverse(*args, **kwargs), 'en')


class AdvertiserMixin:

    def visit_link(self, store_id, url=None, custom=None):
        if url is None:
            url = 'http://www.mystore.com/myproduct/'

        if custom is None:
            response = self.client.get('%s?store_id=%s&url=%s' % (reverse('advertiser-link'), store_id, url))
        else:
            response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))

        self.assertEqual(response.status_code, 302)

        return response

    def checkout(self, *args, **kwargs):
        disable_check = kwargs.pop('disable_check', False)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'),
                                              urllib.urlencode(kwargs)))
        if not disable_check:
            self.assertEqual(response.status_code, 200)

        return response


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class AdvertiserConversionPixelTest(TransactionTestCase, AdvertiserMixin):

    def setUp(self):
        """
        Initialize two users. One user has a store assigned the other does not.
        """
        cache.delete(settings.APPAREL_RATES_CACHE_KEY)
        FXRate = get_model('importer', 'FXRate')
        FXRate.objects.create(currency='SEK', base_currency='SEK', rate='1.00')
        FXRate.objects.create(currency='EUR', base_currency='SEK', rate='0.118160')
        FXRate.objects.create(currency='SEK', base_currency='EUR', rate='8.612600')
        FXRate.objects.create(currency='EUR', base_currency='EUR', rate='1.00')

        self.admin = get_user_model().objects.create_superuser('admin', 'admin@xvid.se', 'admin')
        self.user1 = get_user_model().objects.create_user('user1', 'user1@xvid.se', 'user1')
        self.user2 = get_user_model().objects.create_user('user2', 'user2@xvid.se', 'user2')
        self.vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        self.store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                    user=self.user1,
                                                                    commission_percentage='0.2',
                                                                    vendor=self.vendor)

    def tearDown(self):
        FXRate = get_model('importer', 'FXRate')
        for rate in FXRate.objects.all():
            del rate

    def test_invalid_order_value(self):
        """
        Test invalid order value.
        """
        response = self.client.get('%s%s' % (reverse('advertiser-pixel'), '?store_id=mystore&order_id=1234&order_value=1234f&currency=SEK'))
        self.assertContains(response, 'Order value must be a number.', count=1, status_code=400)
        self.assertEqual(len(mail.outbox), 3)

    def test_missing_required_parameters(self):
        """
        Test missing required parameters for advertiser conversion pixel.
        """
        response = self.client.get(reverse('advertiser-pixel'))
        self.assertContains(response, 'Missing required parameters.', count=1, status_code=400)

        response = self.client.get('%s?store_id=mystore' % (reverse('advertiser-pixel'),))
        self.assertContains(response, 'Missing required parameters.', count=1, status_code=400)

        response = self.client.get('%s?store_id=mystore&order_id=1234' % (reverse('advertiser-pixel'),))
        self.assertContains(response, 'Missing required parameters.', count=1, status_code=400)

        response = self.client.get('%s?store_id=mystore&order_id=1234&order_value=1234' % (reverse('advertiser-pixel'),))
        self.assertContains(response, 'Missing required parameters.', count=1, status_code=400)

        self.assertEqual(len(mail.outbox), 3)

        with self.assertRaises(Transaction.DoesNotExist):
            Transaction.objects.get(store_id='mystore', order_id=1234)

    def test_required_parameters(self):
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK')

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.INVALID)
        self.assertEqual(transaction.original_order_value, 1234)
        self.assertEqual(transaction.order_value, decimal.Decimal('145.81'))
        self.assertEqual(transaction.original_currency, 'SEK')
        self.assertEqual(transaction.currency, 'EUR')
        self.assertEqual(transaction.original_commission, decimal.Decimal('246.8'))
        self.assertEqual(transaction.commission, decimal.Decimal('29.16'))

    def test_cookie_data(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK')

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.original_order_value, 1234)
        self.assertEqual(transaction.order_value, decimal.Decimal('145.81'))
        self.assertEqual(transaction.original_currency, 'SEK')
        self.assertEqual(transaction.currency, 'EUR')
        self.assertEqual(transaction.original_commission, decimal.Decimal('246.8'))
        self.assertEqual(transaction.commission, decimal.Decimal('29.16'))

    def test_order_detail(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='A1EF1', order_value='1000', currency='EUR', sku='ProductXYZ', quantity='1', price='1000')

        transaction = Transaction.objects.get(store_id='mystore', order_id='A1EF1')
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.original_order_value, decimal.Decimal('1000'))
        self.assertEqual(transaction.order_value, decimal.Decimal('1000'))
        self.assertEqual(transaction.currency, 'EUR')
        self.assertEqual(transaction.commission, decimal.Decimal('200'))

        products = transaction.products.all()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].sku, 'ProductXYZ')
        self.assertEqual(products[0].quantity, 1)
        self.assertEqual(products[0].price, 1000)

    def test_multiple_order_details(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='A1EF1', order_value='599', currency='SEK', sku='ProductXZY^ProductABC', quantity='1^1', price='599^100')

        transaction = Transaction.objects.get(store_id='mystore', order_id='A1EF1')
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, decimal.Decimal('70.78'))
        self.assertEqual(transaction.original_currency, 'SEK')
        self.assertEqual(transaction.currency, 'EUR')
        self.assertEqual(transaction.commission, decimal.Decimal('14.16'))

        products = transaction.products.all()
        self.assertEqual(len(products), 2)

    def test_unbalanced_order_details(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='A1EF1', order_value='599', currency='SEK', sku='ProductXYZ^ProductABC', quantity='1', price='499^100')

        transaction = Transaction.objects.get(store_id='mystore', order_id='A1EF1')
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, decimal.Decimal('70.78'))
        self.assertEqual(transaction.original_currency, 'SEK')
        self.assertEqual(transaction.currency, 'EUR')
        self.assertEqual(transaction.commission, decimal.Decimal('14.16'))

        products = transaction.products.all()
        self.assertEqual(len(products), 1)
        self.assertEqual(len(mail.outbox), 4)
        #self.assertEqual(mail.outbox[3].subject, 'Advertiser Pixel Info: new purchase on %s' % self.store) # It's currenty logging this info, not sending it through email
        # Disabled, see views.py
        #self.assertEqual(mail.outbox[4].subject, 'Advertiser Pixel Warning: order value and individual products value is not equal')

    def test_missing_order_detail_parameter(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='A1EF1', order_value='599', currency='SEK', sku='ProductXYZ', quantity='1')

        transaction = Transaction.objects.get(store_id='mystore', order_id='A1EF1')
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, decimal.Decimal('70.78'))
        self.assertEqual(transaction.original_currency, 'SEK')
        self.assertEqual(transaction.currency, 'EUR')
        self.assertEqual(transaction.commission, decimal.Decimal('14.16'))

        products = transaction.products.all()
        self.assertEqual(len(products), 0)

        self.assertEqual(len(mail.outbox), 4)
        #self.assertEqual(mail.outbox[4].subject, 'Advertiser Pixel Error: missing one or more product parameters')  # It's currenty logging this info, not sending it through email

    def test_no_store_id_in_database(self):
        self.checkout(store_id='invalid_id', order_id='1234', order_value='1234', currency='SEK')

        transaction = Transaction.objects.get(store_id='invalid_id', order_id='1234')
        self.assertEqual(transaction.status, Transaction.INVALID)
        self.assertEqual(transaction.original_order_value, 1234)
        self.assertEqual(transaction.order_value, decimal.Decimal('145.81'))
        self.assertEqual(transaction.original_currency, 'SEK')
        self.assertEqual(transaction.currency, 'EUR')
        self.assertEqual(transaction.commission, decimal.Decimal('0'))

    def test_invalid_product_data(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK', sku='BLABLA', quantity='A', price='1234')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK', sku='BLABLA', quantity='1', price='1234ffff')

        self.assertEqual(len(mail.outbox), 4)
        #self.assertEqual(mail.outbox[3].subject, 'Advertiser Pixel Error: could not convert price or quantity') # It's currenty logging this info, not sending it through email
        #self.assertEqual(mail.outbox[4].subject, 'Advertiser Pixel Error: could not convert price or quantity') # It's currenty logging this info, not sending it through email


    def test_optional_parameters_trailing_caret(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK', sku='ProductABC^ProductXYZ^', quantity='1^1^', price='1000^234^')
        self.assertEqual(len(mail.outbox), 4)

    def test_checkout_same_order_id(self):
        # Checkout conversion pixel
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='XYZ 123', order_value='1000', currency='EUR')
        self.assertEqual(Transaction.objects.count(), 1)

        # Checkout conversion pixel with same order id and unchanged values
        self.checkout(store_id='mystore', order_id='XYZ 123', order_value='1000', currency='EUR')
        self.assertEqual(Transaction.objects.count(), 1)

        transaction = Transaction.objects.get(store_id='mystore', order_id='XYZ 123')
        self.assertEqual(transaction.original_order_value, decimal.Decimal('1000'))
        self.assertEqual(transaction.original_currency, 'EUR')
        self.assertEqual(transaction.order_value, decimal.Decimal('1000'))
        self.assertEqual(transaction.currency, 'EUR')

        # Checkout conversion pixel with same order id and changed order value and currency
        self.checkout(store_id='mystore', order_id='XYZ 123', order_value='10000', currency='SEK')
        self.assertEqual(Transaction.objects.count(), 1)

        transaction = Transaction.objects.get(store_id='mystore', order_id='XYZ 123')
        self.assertEqual(transaction.original_order_value, decimal.Decimal('10000'))
        self.assertEqual(transaction.original_currency, 'SEK')
        self.assertEqual(transaction.order_value, decimal.Decimal('1181.60'))
        self.assertEqual(transaction.currency, 'EUR')

        # Checkout conversion pixel with same order id and invalid order value
        self.checkout(store_id='mystore', order_id='XYZ 123', order_value='', currency='SEK', disable_check=True)
        self.assertEqual(Transaction.objects.count(), 1)

        transaction = Transaction.objects.get(store_id='mystore', order_id='XYZ 123')
        self.assertEqual(transaction.original_order_value, decimal.Decimal('10000'))
        self.assertEqual(transaction.original_currency, 'SEK')
        self.assertEqual(transaction.order_value, decimal.Decimal('1181.60'))
        self.assertEqual(transaction.currency, 'EUR')



@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class AdvertiserLinkTest(TransactionTestCase, AdvertiserMixin):

    def setUp(self):
        """
        Initialize two users. One user has a store assigned the other does not.
        """
        FXRate = get_model('importer', 'FXRate')
        FXRate.objects.create(currency='SEK', base_currency='SEK', rate='1.00')
        FXRate.objects.create(currency='EUR', base_currency='SEK', rate='0.118160')
        FXRate.objects.create(currency='SEK', base_currency='EUR', rate='8.612600')
        FXRate.objects.create(currency='EUR', base_currency='EUR', rate='1.00')

        self.vendor1 = get_model('apparel', 'Vendor').objects.create(name='store1')
        self.vendor2 = get_model('apparel', 'Vendor').objects.create(name='store2')
        self.user1 = get_user_model().objects.create_user('user1', 'user1@xvid.se', 'user1')
        self.user2 = get_user_model().objects.create_user('user2', 'user2@xvid.se', 'user2')
        self.store1 = get_model('advertiser', 'Store').objects.create(identifier='store1',
                                                                    user=self.user1,
                                                                    commission_percentage='0.2',
                                                                    vendor=self.vendor1)
        self.store2 = get_model('advertiser', 'Store').objects.create(identifier='store2',
                                                                     user=self.user2,
                                                                     commission_percentage='0.5',
                                                                     vendor=self.vendor2)

    def test_no_url_parameter(self):
        response = self.client.get(reverse('advertiser-link'))
        self.assertContains(response, 'Missing url parameter.', count=1, status_code=400)

    def test_no_store_id_parameter(self):
        response = self.client.get('%s?url=%s' % (reverse('advertiser-link'), 'http://www.google.com/'))
        self.assertContains(response, 'Missing store_id parameter.', count=1, status_code=400)

    def test_url_parameter(self):
        url = '/sv/shop/women/'

        response = self.client.get('%s?store_id=mystore&url=%s' % (reverse('advertiser-link'), url), follow=True)
        self.assertRedirects(response, url, status_code=302, target_status_code=200)

        url = 'http://www.google.com/'

        response = self.client.get('%s?url=%s&store_id=mystore' % (reverse('advertiser-link'), url))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], url)
        self.assertIn(get_cookie_name('mystore'), response.cookies)

    def test_cookie(self):
        self.visit_link('store1', custom='250-Shop')

        cookie_instance = Cookie.objects.get(store_id='store1')
        self.assertEqual(cookie_instance.custom, '250-Shop')

        self.visit_link('store1', custom='250-Ext-Look')
        self.assertEqual(Cookie.objects.count(), 2)

        cookies = Cookie.objects.filter(store_id='store1').order_by('-created')
        self.assertEqual(cookies[1].custom, '250-Shop')
        self.assertEqual(cookies[0].custom, '250-Ext-Look')
        self.assertEqual(cookies[0].old_cookie_id, cookie_instance.cookie_id)

    def test_multiple_stores(self):
        """
        Test for multiple stores.

        Visit a product link from store1 and then check out on store1 and
        store2 and make sure we only get one pending transaction.
        """
        self.visit_link('store1')

        self.checkout(store_id='store1', order_id='1234', order_value='100', currency='SEK')
        self.checkout(store_id='store2', order_id='5678', order_value='200', currency='SEK')

        transaction = Transaction.objects.get(store_id='store1', order_id=1234)
        self.assertEqual(transaction.status, Transaction.PENDING)

        transaction = Transaction.objects.get(store_id='store2', order_id=5678)
        self.assertEqual(transaction.status, Transaction.INVALID)



    # TODO: how to test cookie date, 30 days?


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class AdvertiserFlowTest(TransactionTestCase, AdvertiserMixin):

    def setUp(self):
        """
        Initialize two users. One user has a store assigned the other does not.
        """
        FXRate = get_model('importer', 'FXRate')
        FXRate.objects.create(currency='SEK', base_currency='SEK', rate='1.00')
        FXRate.objects.create(currency='EUR', base_currency='SEK', rate='0.118160')
        FXRate.objects.create(currency='SEK', base_currency='EUR', rate='8.612600')
        FXRate.objects.create(currency='EUR', base_currency='EUR', rate='1.00')

        self.user1 = get_user_model().objects.create_user('user1', 'user1@xvid.se', 'user1')
        self.user2 = get_user_model().objects.create_user('user2', 'user2@xvid.se', 'user2')
        self.vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        self.store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                    user=self.user1,
                                                                    commission_percentage='0.2',
                                                                    vendor=self.vendor)

    @unittest.skip("Review this test")
    def test_advertiser_flow(self):
        """
        Test advertiser flow.

        First visit a product redirect link which sets a cookie. Then visit the
        checkout page both with a valid and invalid store id.  Then login as the store
        owner and make sure that one converion has been noted.
        """
        # Visit redirect URL and get a cookie
        self.visit_link('mystore')

        # Visit checkout page with conversion pixel
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK')

        # Visit checkout page with conversion pixel with wrong store id
        self.checkout(store_id='mystore_fail', order_id='1234', order_value='1234', currency='SEK')
        # Login
        self.client.login(username='user1', password='user1')

        # Display list
        response = self.client.get(reverse_locale('advertiser-store-admin'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('transactions', response.context)
        self.assertEqual(len(response.context['transactions']), 1)

    def test_admin_view_user_no_store(self):
        """
        """
        self.client.login(username='user2', password='user2')

        response = self.client.get(reverse_locale('advertiser-store-admin'))
        self.assertEqual(response.status_code, 404)

    @unittest.skip("Review this test")
    def test_admin_view_no_user(self):
        """
        """
        response = self.client.get(reverse_locale('advertiser-store-admin'))
        self.assertEqual(response.status_code, 302)

    def test_non_existent_transaction(self):
        self.client.login(username='user1', password='user1')

        response = self.client.get(reverse_locale('advertiser-admin-accept', args=[1000]))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse_locale('advertiser-admin-accept', args=[1000]))
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse_locale('advertiser-admin-reject', args=[1000]))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse_locale('advertiser-admin-reject', args=[1000]))
        self.assertEqual(response.status_code, 404)

    @unittest.skip("Review this test")
    def test_accept_transaction(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK')

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.original_order_value, 1234)
        self.assertEqual(transaction.order_value, decimal.Decimal('145.81'))
        self.assertEqual(transaction.original_currency, 'SEK')
        self.assertEqual(transaction.currency, 'EUR')
        self.assertEqual(transaction.original_commission, decimal.Decimal('246.8'))
        self.assertEqual(transaction.commission, decimal.Decimal('29.16'))

        store = Store.objects.get(user=self.user1)
        self.assertEqual(store.balance, 0)

        self.client.login(username='user1', password='user1')

        response = self.client.get(reverse_locale('advertiser-admin-accept', args=[transaction.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse_locale('advertiser-admin-accept', args=[transaction.pk]))
        self.assertEqual(response.status_code, 200)

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.ACCEPTED)
        self.assertTrue(transaction.status_date)

        store = Store.objects.get(user=self.user1)
        self.assertEqual(store.balance, decimal.Decimal('-29.16'))

        store_history = StoreHistory.objects.filter(store=store)
        self.assertEqual(store_history.count(), 2)

        # Accept another transaction
        self.checkout(store_id='mystore', order_id='12345', order_value='10', currency='EUR')
        transaction = Transaction.objects.get(store_id='mystore', order_id=12345)
        response = self.client.post(reverse_locale('advertiser-admin-accept', args=[transaction.pk]))

        store = Store.objects.get(user=self.user1)
        self.assertEqual(store.balance, decimal.Decimal('-31.16'))

        store_history = StoreHistory.objects.filter(store=store)
        self.assertEqual(store_history.count(), 3)

    @unittest.skip("Review this test")
    def test_reject_transaction(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK')

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.original_order_value, 1234)
        self.assertEqual(transaction.order_value, decimal.Decimal('145.81'))
        self.assertEqual(transaction.original_currency, 'SEK')
        self.assertEqual(transaction.currency, 'EUR')
        self.assertEqual(transaction.original_commission, decimal.Decimal('246.8'))
        self.assertEqual(transaction.commission, decimal.Decimal('29.16'))

        self.client.login(username='user1', password='user1')

        response = self.client.get(reverse_locale('advertiser-admin-reject', args=[transaction.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse_locale('advertiser-admin-reject', args=[transaction.pk]), {'message': 'wrong price'})
        self.assertEqual(response.status_code, 200)

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.REJECTED)
        self.assertEqual(transaction.status_message, 'wrong price')
        self.assertTrue(transaction.status_date)