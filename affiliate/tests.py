"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.core.urlresolvers import reverse
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model

from affiliate.views import AFFILIATE_COOKIE_NAME
from affiliate.models import Transaction


class AffiliateConversionPixelTest(TransactionTestCase):

    def _visit_link(self):
        url = 'http://www.mystore.com/myproduct/'
        response = self.client.get('%s?url=%s' % (reverse('affiliate-link'), url))

    def setUp(self):
        pass

    def test_missing_required_parameters(self):
        """
        Test missing required parameters for affiliate conversion pixel.
        """
        response = self.client.get(reverse('affiliate-pixel'))
        self.assertEqual(response.status_code, 400)

        response = self.client.get('%s?store_id=mystore' % (reverse('affiliate-pixel'),))
        self.assertEqual(response.status_code, 400)

        response = self.client.get('%s?store_id=mystore&order_id=1234' % (reverse('affiliate-pixel'),))
        self.assertEqual(response.status_code, 400)

        with self.assertRaises(Transaction.DoesNotExist):
            Transaction.objects.get(store_id='mystore', order_id=1234)

    def test_required_parameters(self):
        response = self.client.get('%s%s' % (reverse('affiliate-pixel'), '?store_id=mystore&order_id=1234&order_value=1234&currency=SEK'))
        self.assertEqual(response.status_code, 200)

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.INVALID)

    def test_cookie_data(self):
        self._visit_link()

        response = self.client.get('%s%s' % (reverse('affiliate-pixel'), '?store_id=mystore&order_id=1234&order_value=1234&currency=SEK'))
        self.assertEqual(response.status_code, 200)

        transaction = Transaction.objects.get(store_id='mystore', order_id=1234)
        self.assertEqual(transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.order_value, 1234)
        self.assertEqual(transaction.currency, 'SEK')

    def test_order_detail(self):
        pass


class AffiliateLinkTest(TestCase):

    def test_no_url_parameter(self):
        response = self.client.get(reverse('affiliate-link'))
        self.assertContains(response, 'Missing url parameter.', count=1, status_code=400)

    def test_url_parameter(self):
        url = '/shop/women/'

        response = self.client.get('%s?url=%s' % (reverse('affiliate-link'), url), follow=True)
        self.assertRedirects(response, url, status_code=302, target_status_code=200)

        url = 'http://www.google.com/'

        response = self.client.get('/a/link/?url=%s' % (url,))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], url)
        self.assertIn(AFFILIATE_COOKIE_NAME, response.cookies)

    # TODO: how to test cookie date, 30 days?


class AffiliateFlowTest(TestCase):

    def setUp(self):
        """
        Initialize two users. One user has a store assigned the other does not.
        """
        self.user1 = get_user_model().objects.create_user('user1', 'user1@xvid.se', 'user1')
        self.user2 = get_user_model().objects.create_user('user2', 'user2@xvid.se', 'user2')
        self.store = get_model('affiliate', 'Store').objects.create(identifier='mystore', user=self.user1)

    def test_affiliate_flow(self):
        """
        Test affiliate flow.

        First visit a product redirect link which sets a cookie. Then visit the
        checkout page both with a valid and invalid store id.  Then login as the store
        owner and make sure that one converion has been noted.
        """
        url = 'http://www.mystore.com/myproduct/'

        # Visit redirect URL and get a cookie
        response = self.client.get('/a/link/?url=%s' % (url,))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], url)
        self.assertIn(AFFILIATE_COOKIE_NAME, response.cookies)

        # Visit checkout page with conversion pixel
        response = self.client.get('/a/conversion/?store_id=mystore&order_id=1234&order_value=1234&currency=SEK')
        self.assertEqual(response.status_code, 200)

        # Visit checkout page with conversion pixel with wrong store id
        response = self.client.get('/a/conversion/?store_id=mystore_fail&order_id=1234&order_value=1234&currency=SEK')
        self.assertEqual(response.status_code, 200)

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
