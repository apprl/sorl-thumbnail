"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import decimal
import urllib

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model

from affiliate.views import get_cookie_name
from affiliate.models import Transaction, Store, StoreHistory, Cookie

class AffiliateMixin:

    def visit_link(self, store_id, url=None, custom=None):
        if url is None:
            url = 'http://www.mystore.com/myproduct/'

        if custom is None:
            response = self.client.get('%s?store_id=%s&url=%s' % (reverse('affiliate-link'), store_id, url))
        else:
            response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('affiliate-link'), store_id, url, custom))

        self.assertEqual(response.status_code, 302)

        return response

    def checkout(self, *args, **kwargs):
        response = self.client.get('%s?%s' % (reverse('affiliate-pixel'),
                                              urllib.urlencode(kwargs)))
        self.assertEqual(response.status_code, 200)

        return response


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class AffiliateConversionPixelTest(TransactionTestCase, AffiliateMixin):

    def setUp(self):
        """
        Initialize two users. One user has a store assigned the other does not.
        """
        self.admin = get_user_model().objects.create_superuser('admin', 'admin@xvid.se', 'admin')
        self.user1 = get_user_model().objects.create_user('user1', 'user1@xvid.se', 'user1')
        self.user2 = get_user_model().objects.create_user('user2', 'user2@xvid.se', 'user2')
        self.vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        self.store = get_model('affiliate', 'Store').objects.create(identifier='mystore',
                                                                    user=self.user1,
                                                                    commission_percentage='0.2',
                                                                    vendor=self.vendor)

    def test_invalid_order_value(self):
        """
        Test invalid order value.
        """
        response = self.client.get('%s%s' % (reverse('affiliate-pixel'), '?store_id=mystore&order_id=1234&order_value=1234f&currency=SEK'))
        self.assertContains(response, 'Order value must be a number.', count=1, status_code=400)
        self.assertEqual(len(mail.outbox), 1)

    def test_missing_required_parameters(self):
        """
        Test missing required parameters for affiliate conversion pixel.
        """
        response = self.client.get(reverse('affiliate-pixel'))
        self.assertContains(response, 'Missing required parameters.', count=1, status_code=400)

        response = self.client.get('%s?store_id=mystore' % (reverse('affiliate-pixel'),))
        self.assertContains(response, 'Missing required parameters.', count=1, status_code=400)

        response = self.client.get('%s?store_id=mystore&order_id=1234' % (reverse('affiliate-pixel'),))
        self.assertContains(response, 'Missing required parameters.', count=1, status_code=400)

        response = self.client.get('%s?store_id=mystore&order_id=1234&order_value=1234' % (reverse('affiliate-pixel'),))
        self.assertContains(response, 'Missing required parameters.', count=1, status_code=400)

        self.assertEqual(len(mail.outbox), 4)

        with self.assertRaises(Transaction.DoesNotExist):
            Transaction.objects.get(store_id='mystore', order_id=1234)

    def test_required_parameters(self):
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK')

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.INVALID)
        self.assertEqual(transaction.order_value, 1234)
        self.assertEqual(transaction.currency, 'SEK')
        self.assertEqual(transaction.commission, decimal.Decimal('246.8'))

    def test_cookie_data(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK')

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, 1234)
        self.assertEqual(transaction.currency, 'SEK')
        self.assertEqual(transaction.commission, decimal.Decimal('246.8'))

    def test_order_detail(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='A1EF1', order_value='599', currency='SEK', sku='ProductXYZ', quantity='1', price='599')

        transaction = Transaction.objects.get(store_id='mystore', order_id='A1EF1')
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, 599)
        self.assertEqual(transaction.currency, 'SEK')
        self.assertEqual(transaction.commission, decimal.Decimal('119.8'))

        products = transaction.products.all()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].sku, 'ProductXYZ')
        self.assertEqual(products[0].quantity, 1)
        self.assertEqual(products[0].price, 599)

    def test_multiple_order_details(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='A1EF1', order_value='699', currency='SEK', sku='ProductXZY^ProductABC', quantity='1^1', price='599^100')

        transaction = Transaction.objects.get(store_id='mystore', order_id='A1EF1')
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, 699)
        self.assertEqual(transaction.currency, 'SEK')
        self.assertEqual(transaction.commission, decimal.Decimal('139.8'))

        products = transaction.products.all()
        self.assertEqual(len(products), 2)

    def test_unbalanced_order_details(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='A1EF1', order_value='699', currency='SEK', sku='ProductXYZ^ProductABC', quantity='1', price='599^100')

        transaction = Transaction.objects.get(store_id='mystore', order_id='A1EF1')
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, 699)
        self.assertEqual(transaction.currency, 'SEK')
        self.assertEqual(transaction.commission, decimal.Decimal('139.8'))

        products = transaction.products.all()
        self.assertEqual(len(products), 1)

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].subject, 'Advertiser Pixel Warning: length of every product parameter is not consistent')
        self.assertEqual(mail.outbox[1].subject, 'Advertiser Pixel Warning: order value and individual products value is not equal')

    def test_missing_order_detail_parameter(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='A1EF1', order_value='599', currency='SEK', sku='ProductXYZ', quantity='1')

        transaction = Transaction.objects.get(store_id='mystore', order_id='A1EF1')
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, 599)
        self.assertEqual(transaction.currency, 'SEK')
        self.assertEqual(transaction.commission, decimal.Decimal('119.8'))

        products = transaction.products.all()
        self.assertEqual(len(products), 0)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Advertiser Pixel Error: missing one or more product parameters')

    def test_no_store_id_in_database(self):
        self.checkout(store_id='invalid_id', order_id='1234', order_value='1234', currency='SEK')

        transaction = Transaction.objects.get(store_id='invalid_id', order_id='1234')
        self.assertEqual(transaction.status, Transaction.INVALID)
        self.assertEqual(transaction.order_value, 1234)
        self.assertEqual(transaction.currency, 'SEK')
        self.assertEqual(transaction.commission, decimal.Decimal('0'))

    def test_invalid_product_data(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK', sku='BLABLA', quantity='A', price='1234')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK', sku='BLABLA', quantity='1', price='1234ffff')

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].subject, 'Advertiser Pixel Error: could not convert price or quantity')
        self.assertEqual(mail.outbox[1].subject, 'Advertiser Pixel Error: could not convert price or quantity')


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class AffiliateLinkTest(TransactionTestCase, AffiliateMixin):

    def setUp(self):
        """
        Initialize two users. One user has a store assigned the other does not.
        """
        self.vendor1 = get_model('apparel', 'Vendor').objects.create(name='store1')
        self.vendor2 = get_model('apparel', 'Vendor').objects.create(name='store2')
        self.user1 = get_user_model().objects.create_user('user1', 'user1@xvid.se', 'user1')
        self.user2 = get_user_model().objects.create_user('user2', 'user2@xvid.se', 'user2')
        self.store1 = get_model('affiliate', 'Store').objects.create(identifier='store1',
                                                                    user=self.user1,
                                                                    commission_percentage='0.2',
                                                                    vendor=self.vendor1)
        self.store2 = get_model('affiliate', 'Store').objects.create(identifier='store2',
                                                                     user=self.user2,
                                                                     commission_percentage='0.5',
                                                                     vendor=self.vendor2)

    def test_no_url_parameter(self):
        response = self.client.get(reverse('affiliate-link'))
        self.assertContains(response, 'Missing url parameter.', count=1, status_code=400)

    def test_no_store_id_parameter(self):
        response = self.client.get('%s?url=%s' % (reverse('affiliate-link'), 'http://www.google.com/'))
        self.assertContains(response, 'Missing store_id parameter.', count=1, status_code=400)

    def test_url_parameter(self):
        url = '/shop/women/'

        response = self.client.get('%s?store_id=mystore&url=%s' % (reverse('affiliate-link'), url), follow=True)
        self.assertRedirects(response, url, status_code=302, target_status_code=200)

        url = 'http://www.google.com/'

        response = self.client.get('%s?url=%s&store_id=mystore' % (reverse('affiliate-link'), url))
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
class AffiliateFlowTest(TransactionTestCase, AffiliateMixin):

    def setUp(self):
        """
        Initialize two users. One user has a store assigned the other does not.
        """
        self.user1 = get_user_model().objects.create_user('user1', 'user1@xvid.se', 'user1')
        self.user2 = get_user_model().objects.create_user('user2', 'user2@xvid.se', 'user2')
        self.vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        self.store = get_model('affiliate', 'Store').objects.create(identifier='mystore',
                                                                    user=self.user1,
                                                                    commission_percentage='0.2',
                                                                    vendor=self.vendor)


    def test_affiliate_flow(self):
        """
        Test affiliate flow.

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
        response = self.client.get(reverse('affiliate-store-admin'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('transactions', response.context)
        self.assertEqual(len(response.context['transactions']), 1)

    def test_admin_view_user_no_store(self):
        """
        """
        self.client.login(username='user2', password='user2')

        response = self.client.get(reverse('affiliate-store-admin'))
        self.assertEqual(response.status_code, 404)

    def test_admin_view_no_user(self):
        """
        """
        response = self.client.get(reverse('affiliate-store-admin'))
        self.assertEqual(response.status_code, 302)

    def test_non_existent_transaction(self):
        self.client.login(username='user1', password='user1')

        response = self.client.get(reverse('affiliate-admin-accept', args=[1000]))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse('affiliate-admin-accept', args=[1000]))
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse('affiliate-admin-reject', args=[1000]))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse('affiliate-admin-reject', args=[1000]))
        self.assertEqual(response.status_code, 404)

    def test_accept_transaction(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK')

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, 1234)
        self.assertEqual(transaction.currency, 'SEK')
        self.assertEqual(transaction.commission, decimal.Decimal('246.8'))

        store = Store.objects.get(user=self.user1)
        self.assertEqual(store.balance, 0)

        self.client.login(username='user1', password='user1')

        response = self.client.get(reverse('affiliate-admin-accept', args=[transaction.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('affiliate-admin-accept', args=[transaction.pk]))
        self.assertEqual(response.status_code, 200)

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.ACCEPTED)
        self.assertTrue(transaction.status_date)

        store = Store.objects.get(user=self.user1)
        self.assertEqual(store.balance, decimal.Decimal('246.8'))

        store_history = StoreHistory.objects.filter(store=store)
        self.assertEqual(store_history.count(), 2)

        # Accept another transaction
        self.checkout(store_id='mystore', order_id='12345', order_value='100', currency='SEK')
        transaction = Transaction.objects.get(store_id='mystore', order_id=12345)
        response = self.client.post(reverse('affiliate-admin-accept', args=[transaction.pk]))

        store = Store.objects.get(user=self.user1)
        self.assertEqual(store.balance, decimal.Decimal('266.8'))

        store_history = StoreHistory.objects.filter(store=store)
        self.assertEqual(store_history.count(), 3)

    def test_reject_transaction(self):
        self.visit_link('mystore')
        self.checkout(store_id='mystore', order_id='1234', order_value='1234', currency='SEK')

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, 1234)
        self.assertEqual(transaction.currency, 'SEK')
        self.assertEqual(transaction.commission, decimal.Decimal('246.8'))

        self.client.login(username='user1', password='user1')

        response = self.client.get(reverse('affiliate-admin-reject', args=[transaction.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('affiliate-admin-reject', args=[transaction.pk]), {'message': 'wrong price'})
        self.assertEqual(response.status_code, 200)

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.REJECTED)
        self.assertEqual(transaction.status_message, 'wrong price')
        self.assertTrue(transaction.status_date)
