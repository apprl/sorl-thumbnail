import re
import datetime
import urllib
import decimal
import os
import calendar
import json
from django.db.models import Sum
from apparelrow.dashboard.factories import *


from django.conf import settings
from django.core import mail
from django.core import signing
from django.core.urlresolvers import reverse as _reverse
from django.test import TransactionTestCase, TestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.core import management

from localeurl.utils import locale_url
from apparelrow.apparel.models import Vendor
from apparelrow.dashboard.models import Group, StoreCommission, Cut, Sale

from apparelrow.dashboard.utils import get_cuts_for_user_and_vendor, get_total_clicks_per_vendor
from apparelrow.apparel.utils import currency_exchange
from django.core.cache import cache



def reverse(*args, **kwargs):
    return locale_url(_reverse(*args, **kwargs), 'en')


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestDashboard(TransactionTestCase):

    def setUp(self):
        FXRate = get_model('importer', 'FXRate')
        FXRate.objects.create(currency='SEK', base_currency='SEK', rate='1.00')
        FXRate.objects.create(currency='EUR', base_currency='SEK', rate='0.118160')
        FXRate.objects.create(currency='SEK', base_currency='EUR', rate='8.612600')
        FXRate.objects.create(currency='EUR', base_currency='EUR', rate='1.00')

    def test_generate_referral_code(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.save()

        self.assertFalse(referral_user.referral_partner)

        referral_user.is_partner = True
        referral_user.referral_partner = True
        referral_user.save()

        self.assertIsNotNone(referral_user.referral_partner_code)

        another_user = get_user_model().objects.create_user('another_user', 'another@xvid.se', 'password')
        another_user.referral_partner = True
        another_user.is_partner = True
        another_user.save()

        self.assertIsNotNone(another_user.referral_partner_code)
        self.assertNotEqual(another_user.referral_partner_code, referral_user.referral_partner_code)

    def test_no_referral_link_for_normal_user(self):
        normal_user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')

        self.assertEqual(normal_user.referral_partner, False)
        self.assertFalse(normal_user.referral_partner_code)
        self.assertEqual(normal_user.get_referral_url(), None)

    #@unittest.skip("Review this test")
    def test_referral_link(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        referral_url = referral_user.get_referral_url()
        self.assertRegexpMatches(referral_url, r'\/i\/\w{4,16}')

        response = self.client.get(referral_url, follow=True)
        redirect = reverse('publisher-contact')
        self.assertRedirects(response, redirect)
        self.assertIn(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME, response.client.cookies.keys())

        # decode cookie manually and verify content
        cookie_key = settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME
        signed_cookie_value = response.client.cookies.get(cookie_key).value
        value = signing.get_cookie_signer(salt=cookie_key).unsign(signed_cookie_value, max_age=None)
        self.assertEqual(str(value), str(referral_user.pk))

    #@unittest.skip("Review this test")
    def test_referral_link_disabled(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        referral_url = referral_user.get_referral_url()
        self.assertRegexpMatches(referral_url, r'\/i\/\w{4,16}')

        referral_user.referral_partner = False
        referral_user.save()

        response = self.client.get(referral_url, follow=True)
        self.assertRedirects(response, reverse('publisher-contact'))
        self.assertNotIn(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME, response.client.cookies.keys())

    #@unittest.skip("Review this test")
    def test_publisher_signup_from_referral_link(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        normal_user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')

        response = self.client.get(referral_user.get_referral_url(), follow=True)
        response = self.client.post(reverse('publisher-contact'), {'name': 'test', 'email': 'test@test.com', 'blog': 'blog'})

        instance = get_model('dashboard', 'Signup').objects.get()
        self.assertEqual(instance.name, 'test')
        self.assertEqual(instance.email, 'test@test.com')
        self.assertEqual(instance.blog, 'blog')
        self.assertEqual(instance.store, False)
        self.assertEqual(instance.referral_user, referral_user)

        self.assertEqual(len(mail.outbox), 3)

    #@unittest.skip("Review this test")
    def test_publisher_signup_from_referral_link_already_authenticated(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        normal_user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        is_logged_in = self.client.login(username='normal_user', password='normal')
        self.assertTrue(is_logged_in)

        response = self.client.get(referral_user.get_referral_url(), follow=True)
        response = self.client.post(reverse('publisher-contact'), {'name': 'test', 'email': 'test@test.com', 'blog': 'blog'})

        instance = get_model('dashboard', 'Signup').objects.get()
        self.assertEqual(instance.name, 'test')
        self.assertEqual(instance.email, 'test@test.com')
        self.assertEqual(instance.blog, 'blog')
        self.assertEqual(instance.store, False)
        self.assertEqual(instance.referral_user, referral_user)

        self.assertEqual(len(mail.outbox), 3)

    #@unittest.skip("Review this test")
    def test_signup_from_referral_link(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()
        self.assertIsNotNone(referral_user.get_referral_url())

        # Visit referral URL
        response = self.client.get(referral_user.get_referral_url(), follow=True)
        self.assertRedirects(response, reverse('publisher-contact'))

        # Register by email
        response = self.client.post(reverse('auth_register_email'), {'first_name': 'test',
                                                                     'last_name': 'svensson',
                                                                     'username': 'test',
                                                                     'email': 'test@xvid.se',
                                                                     'password1': 'test',
                                                                     'password2': 'test',
                                                                     'gender': 'M'})
        self.assertEquals(response.status_code,302)
        registered_user = get_user_model().objects.get(email='test@xvid.se')
        self.assertIsNotNone(registered_user)

        welcome_mail_body = mail.outbox[2].body
        activation_url = re.search(r'http:\/\/testserver(.+)', welcome_mail_body).group(1)
        # Sometimes a trailing \r is caugt
        activation_url = activation_url.strip()
        self.assertTrue("\r" not in activation_url)
        print "Activation URL found in email: %s" % activation_url
        response = self.client.get(activation_url, follow=True)
        print "Requesting url, status code: %s" % response.status_code
        if response.status_code == 404:
            print "Available activation codes in database:"
            for user in get_user_model().objects.all():
                print "Code: %s" % user.confirmation_key
        self.assertTrue(response.status_code in [200,201],"User activation for %s has failed, responsecode: %s" % (registered_user,response.status_code))
        # We should now be marked with a parent user (from referral URL)
        registered_user = get_user_model().objects.get(email='test@xvid.se')
        self.assertEqual(registered_user.referral_partner_parent, referral_user)
        self.assertIsNone(registered_user.referral_partner_parent_date)

        # Admin goes in and mark the user as partner which in turn sets the
        # parent date and adds 20 EUR to the account
        registered_user.is_partner = True
        registered_user.save()
        self.assertIsNotNone(registered_user.referral_partner_parent_date)

        sale = get_model('dashboard', 'Sale').objects.get(is_promo=True)
        self.assertFalse(sale.is_referral_sale)
        self.assertIsNone(sale.referral_user)
        self.assertTrue(sale.is_promo)
        self.assertEqual(sale.commission, decimal.Decimal(20))
        self.assertEqual(sale.currency, 'EUR')

    #@unittest.skip("Review this test")
    def test_signup_from_own_referral_link(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        is_logged_in = self.client.login(username='referral_user', password='referral')
        self.assertTrue(is_logged_in)

        response = self.client.get(referral_user.get_referral_url(), follow=True)
        self.assertRedirects(response, reverse('publisher-contact'))

        referral_user = get_user_model().objects.get(username='referral_user')
        self.assertIsNone(referral_user.referral_partner_parent)
        self.assertIsNone(referral_user.referral_partner_parent_date)

    #@unittest.skip("Review this test")
    def test_signup_from_invalid_referral_link(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        # Visit referral URL
        response = self.client.get(referral_user.get_referral_url(), follow=True)
        self.assertRedirects(response, reverse('publisher-contact'))

        referral_user.referral_partner = False
        referral_user.save()

        response = self.client.post(reverse('auth_register_email'), {'first_name': 'test',
                                                                     'last_name': 'svensson',
                                                                     'username': 'test',
                                                                     'email': 'test@xvid.se',
                                                                     'password1': 'test',
                                                                     'password2': 'test',
                                                                     'gender': 'M'})
        self.assertEquals(response.status_code,302)
        welcome_mail_body = mail.outbox[2].body
        activation_url = re.search(r'http:\/\/testserver(.+)', welcome_mail_body).group(1)
        response = self.client.get(activation_url)

        registered_user = get_user_model().objects.get(email='test@xvid.se')
        self.assertIsNone(registered_user.referral_partner_parent)
        self.assertIsNone(registered_user.referral_partner_parent_date)

        # Invalid referral link should not result in a promo sale of 20 EUR
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 0)

    #@unittest.skip("Review this test")
    def test_visit_two_referral_links(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        # Visit referral URL, register by email and activate account
        response = self.client.get(referral_user.get_referral_url(), follow=True)
        response = self.client.post(reverse('auth_register_email'), {'first_name': 'test',
                                                                     'last_name': 'svensson',
                                                                     'username': 'test',
                                                                     'email': 'test@xvid.se',
                                                                     'password1': 'test',
                                                                     'password2': 'test',
                                                                     'gender': 'M'})
        welcome_mail_body = mail.outbox[2].body
        activation_url = re.search(r'http:\/\/testserver(.+)', welcome_mail_body).group(1)
        activation_url = activation_url.strip()
        response = self.client.get(activation_url)

        registered_user = get_user_model().objects.get(email='test@xvid.se')
        self.assertEqual(registered_user.referral_partner_parent, referral_user)
        self.assertIsNone(registered_user.referral_partner_parent_date)

        # Admin goes in and mark the user as partner which in turn sets the parent date
        registered_user.is_partner = True
        registered_user.save()

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        another_user = get_user_model().objects.create_user('another_user', 'another@xvid.se', 'another')
        another_user.referral_partner = True
        another_user.is_partner = True
        another_user.save()

        response = self.client.get(another_user.get_referral_url(), follow=True)
        response = self.client.get('/')

        registered_user = get_user_model().objects.get(email='test@xvid.se')
        self.assertEqual(registered_user.referral_partner_parent, referral_user)
        self.assertIsNotNone(registered_user.referral_partner_parent_date)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

    #@unittest.skip("Review this test")
    def test_referral_sale(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        # Visit referral URL, register by email and activate account
        response = self.client.get(referral_user.get_referral_url(), follow=True)
        self.assertTrue(response.status_code in [200,201])
        response = self.client.post(reverse('auth_register_email'), {'first_name': 'test',
                                                                     'last_name': 'svensson',
                                                                     'username': 'test',
                                                                     'email': 'test@xvid.se',
                                                                     'password1': 'test',
                                                                     'password2': 'test',
                                                                     'gender': 'M'})
        self.assertEquals(response.status_code,302)
        welcome_mail_body = mail.outbox[2].body
        activation_url = re.search(r'http:\/\/testserver(.+)', welcome_mail_body).group(1)
        activation_url = activation_url.strip()
        response = self.client.get(activation_url)
        registered_user = get_user_model().objects.get(email='test@xvid.se')

        # Admin goes in and mark the user as partner which in turn sets the parent date
        registered_user.is_partner = True
        registered_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)
        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (registered_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 2) # referral sale and referral signup

        # Verify it
        referral_signup_sale = get_model('dashboard', 'Sale').objects.get(is_referral_sale=False)
        self.assertTrue(referral_signup_sale.is_promo)

        referral_user_sale = get_model('dashboard', 'Sale').objects.get(is_promo=False)
        self.assertTrue(referral_user_sale.is_referral_sale)

        # This test
        #self.assertEqual(referral_user_sale.referral_user, referral_user)
        #self.assertEqual(referral_user_sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

        # Repeat the import of the sale transaction
        #management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        #self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        # Verify it
        #referral_user_sale = get_model('dashboard', 'Sale').objects.get(is_promo=False, is_referral_sale=True)
        #self.assertTrue(referral_user_sale.is_referral_sale)
        #self.assertEqual(referral_user_sale.referral_user, referral_user)
        #self.assertEqual(referral_user_sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

    def test_referred_user_get_20_eur(self):
        pass


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestDashboardCuts(TransactionTestCase):

    def setUp(self):
        FXRate = get_model('importer', 'FXRate')
        FXRate.objects.create(currency='SEK', base_currency='SEK', rate='1.00')
        FXRate.objects.create(currency='EUR', base_currency='SEK', rate='0.118160')
        FXRate.objects.create(currency='SEK', base_currency='EUR', rate='8.612600')
        FXRate.objects.create(currency='EUR', base_currency='EUR', rate='1.00')

    def _create_partner_user(self,username='user'):
        user = get_user_model().objects.create_user(username, 'user@xvid.se', 'user')
        user.is_partner = True
        user.save()

        return user

    def _create_transaction(self, user, store_id=None, order_value=None, order_id=None):
        if store_id is None:
            store_id = 'mystore'

        if order_value is None:
            order_value = '500'

        if order_id is None:
            order_id = '1234-order'

        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name=store_id)
        store = get_model('advertiser', 'Store').objects.create(identifier=store_id, user=store_user, commission_percentage='0.2', vendor=vendor)
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id=order_id, order_value=order_value, currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        return vendor, get_model('advertiser', 'Transaction').objects.get(store_id=store_id, order_id=order_id)

    def test_default_cut(self):
        user = self._create_partner_user()
        vendor, transaction = self._create_transaction(user, order_value='500')
        self.assertTrue(vendor.is_cpo)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        # Verify sale transaction
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
        self.assertEqual(sale.type, Sale.COST_PER_ORDER)
        self.assertIsNotNone(sale)
        self.assertEqual(sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

    def test_non_default_cut(self):
        user = self._create_partner_user()
        vendor, transaction = self._create_transaction(user, order_value='500')
        self.assertTrue(vendor.is_cpo)

        # Create group + cut for store vendor
        group = get_model('dashboard', 'Group').objects.create(name='group_name')
        cuts = get_model('dashboard', 'Cut').objects.create(vendor=vendor, group=group, cut='0.9')
        user.partner_group = group
        user.save()

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        # Verify sale transaction
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
        self.assertEqual(sale.type, Sale.COST_PER_ORDER)
        self.assertIsNotNone(sale)
        self.assertEqual(sale.commission, decimal.Decimal(100) * decimal.Decimal('0.9'))

    def test_update_cut(self):
        user = self._create_partner_user()
        vendor, transaction = self._create_transaction(user, order_value='500')
        self.assertTrue(vendor.is_cpo)

        # Create group + cut for store vendor
        group = get_model('dashboard', 'Group').objects.create(name='group_name')
        cuts = get_model('dashboard', 'Cut').objects.create(vendor=vendor, group=group, cut='0.8')
        user.partner_group = group
        user.save()

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        # Verify sale transaction
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
        self.assertEqual(sale.type, Sale.COST_PER_ORDER)
        self.assertIsNotNone(sale)
        self.assertEqual(sale.commission, decimal.Decimal(100) * decimal.Decimal('0.8'))
        self.assertEqual(sale.cut, decimal.Decimal('0.8'))

        # Update cut
        cuts.cut = '0.5'
        cuts.save()

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        # Verify sale transaction
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
        self.assertIsNotNone(sale)
        self.assertEqual(sale.commission, decimal.Decimal(100) * decimal.Decimal('0.8'))
        self.assertEqual(sale.cut, decimal.Decimal('0.8'))

    def test_do_not_update_after_paid_ready_status(self):
        user = self._create_partner_user()
        payment_detail = get_model('profile', 'PaymentDetail').objects.create(name='a', company='b', orgnr='c', user=user)
        vendor, transaction = self._create_transaction(user, order_value='1000')
        self.assertTrue(vendor.is_cpo)

        group = get_model('dashboard', 'Group').objects.create(name='mygroup')
        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, referral_cut=0.2)

        user.partner_group = group
        user.save()

        # 1. Import the sale transaction and verify it
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
        self.assertEqual(sale.type, Sale.COST_PER_ORDER)
        self.assertEqual(sale.commission, decimal.Decimal(200) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        self.assertEqual(sale.paid, get_model('dashboard', 'Sale').PAID_PENDING)

        # Set transaction as accepted
        transaction = get_model('advertiser', 'Transaction').objects.get()
        transaction.status = get_model('advertiser', 'Transaction').ACCEPTED
        transaction.save()

        # 2. Import the sale transaction again and verify it
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
        self.assertEqual(sale.commission, decimal.Decimal(200) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').CONFIRMED)
        self.assertEqual(sale.paid, get_model('dashboard', 'Sale').PAID_PENDING)

        # Update commission after the sale transaction has been marked as ready for payment
        transaction = get_model('advertiser', 'Transaction').objects.get()
        transaction.order_value = decimal.Decimal('2000')
        transaction.commission = decimal.Decimal('400')
        transaction.save()

        # 3. Import the sale transaction again and verify it
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
        #self.assertEqual(sale.commission, decimal.Decimal(400) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').CONFIRMED)
        self.assertEqual(sale.paid, get_model('dashboard', 'Sale').PAID_PENDING)

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        # Update commission after the sale transaction has been marked as ready for payment
        transaction = get_model('advertiser', 'Transaction').objects.get()
        transaction.order_value = decimal.Decimal('500')
        transaction.commission = decimal.Decimal('100')
        transaction.save()

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 2)

        # 4. Import the sale transaction again and verify it
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
        #self.assertEqual(sale.commission, decimal.Decimal(400) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))
        for earning in sale.userearning_set.all():
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').CONFIRMED)
            if earning.user_earning_type == "publisher_sale_commission":
                self.assertEqual(earning.paid, get_model('dashboard', 'Sale').PAID_READY)
            if earning.user_earning_type == "apprl_commission":
                self.assertEqual(earning.paid, get_model('dashboard', 'Sale').PAID_PENDING)

    def test_parse_and_calculate_store_commissions(self):
        from decimal import Decimal
        user = self._create_partner_user('bluebeltch')
        partner_user = self._create_partner_user()
        group = Group.objects.create(name="TestGroup")
        user.owner_network = partner_user
        partner_user.owner_network_cut = 0.1
        partner_user.save()
        user.partner_group = group
        user.save()
        vendor = Vendor.objects.create(name="TestVendor",homepage="http://www.example.com",provider="aaa")
        self.assertTrue(vendor.is_cpo)

        cut = Cut.objects.create(vendor=vendor, group=group, cut=0.9)
        store_commission = StoreCommission.objects.create(vendor=vendor,commission="6/10/0")

        user_remote, normal_cut, referral_cut, publisher_cut = get_cuts_for_user_and_vendor(user.id,vendor)
        self.assertEquals(user,user_remote)
        self.assertEquals(normal_cut, Decimal('0.9'))
        self.assertEquals(referral_cut,Decimal('0.15'))
        self.assertEquals(publisher_cut,Decimal('0.9'))

        store_commission.calculated_commissions(store_commission.commission, *get_cuts_for_user_and_vendor(user.id,vendor))

        self.assertEquals(store_commission.commission, "5-8%")


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestDashboardUtils(TransactionTestCase):

    def test_cuts(self):
        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')

        user, normal_cut, referral_cut, _ = get_cuts_for_user_and_vendor(temp_user.pk, None)

        self.assertIsNotNone(user)
        self.assertEqual(normal_cut, decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))
        self.assertEqual(referral_cut, decimal.Decimal(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT))

        user, normal_cut, referral_cut, _ = get_cuts_for_user_and_vendor(20321323, None)

        self.assertIsNone(user)
        self.assertEqual(normal_cut, decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))
        self.assertEqual(referral_cut, decimal.Decimal(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT))

    def test_custom_cuts(self):
        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        vendor = get_model('apparel', 'Vendor').objects.create(name='vendor_name')
        group = get_model('dashboard', 'Group').objects.create(name='group_name')
        cuts = get_model('dashboard', 'Cut').objects.create(vendor=vendor, group=group, cut='0.5', referral_cut='0.3')
        temp_user.partner_group = group
        temp_user.save()

        user, normal_cut, referral_cut, _ = get_cuts_for_user_and_vendor(temp_user.pk, vendor)

        self.assertIsNotNone(user)
        self.assertEqual(normal_cut, decimal.Decimal('0.5'))
        self.assertEqual(referral_cut, decimal.Decimal('0.3'))


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestUserEarnings(TransactionTestCase):

    def test_user_earnings_publisher_network(self):
        """ Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
            owner doesn't belong to a Publisher Network
        """
        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.1
        owner_user.save()

        group = get_model('dashboard', 'Group').objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 3)

        earnings = get_model('dashboard', 'UserEarning').objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_network_tribute':
                self.assertEqual(earning.amount, 6.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 54.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').PENDING)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()

        earnings = get_model('dashboard', 'UserEarning').objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').CONFIRMED)

    def test_user_earnings_no_publisher_network(self):
        """ Tests UserEarnings that are generated when the user doesn't belong to a Publisher Network """
        group = get_model('dashboard', 'Group').objects.create(name='mygroup')

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 2)

        earnings = get_model('dashboard', 'UserEarning').objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 60.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').PENDING)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()

        earnings = get_model('dashboard', 'UserEarning').objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').CONFIRMED)

    def test_user_earnings_recursive_publisher_network(self):
        """ Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
            owner belongs to a Publisher Network recursively
        """

        super_master_owner = get_user_model().objects.create_user('super_master_owner', 'super_master_owner@xvid.se', 'super_master_owner')
        super_master_owner.owner_network_cut = 0.5
        super_master_owner.save()

        master_owner = get_user_model().objects.create_user('master_owner', 'master_owner@xvid.se', 'master_owner')
        master_owner.owner_network_cut = 0.2
        master_owner.owner_network = super_master_owner
        master_owner.save()

        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.5
        owner_user.owner_network = master_owner
        owner_user.save()

        group = get_model('dashboard', 'Group').objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 5)

        earnings = get_model('dashboard', 'UserEarning').objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_sale_tribute' and earning.user == owner_user:
                self.assertEqual(earning.amount, 24.000)
            elif earning.user_earning_type == 'publisher_sale_tribute' and earning.user == master_owner:
                self.assertEqual(earning.amount, 3.000)
            elif earning.user_earning_type == 'publisher_sale_tribute' and earning.user == super_master_owner:
                self.assertEqual(earning.amount, 3.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 30.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').PENDING)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()

        earnings = get_model('dashboard', 'UserEarning').objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').CONFIRMED)

    def test_user_earnings_no_commission_group(self):
        """ Tests UserEarnings when user doesn't belong to a Commission Group """
        # User has no Commission Group assigned
        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        # One Sale is generated, no UserEarnings generated
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 0)

        # Create a group and assign it to user
        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.5
        owner_user.save()
        group = get_model('dashboard', 'Group').objects.create(name='mygroup', owner=owner_user)
        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        temp_user.partner_group = group
        temp_user.save()

        # Update Sale status
        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 2)
        earnings = get_model('dashboard', 'UserEarning').objects.all()

        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').CONFIRMED)
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 60.000)

    def test_user_earnings_referral_sale(self):
        """ Tests UserEarnings when a referral Sale is made """
        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.5
        owner_user.save()

        referral_group = get_model('dashboard', 'Group').objects.create(name='mygroup', owner=owner_user)

        referral_user = get_user_model().objects.create_user('referral', 'referral@xvid.se', 'referral')
        referral_user.partner_group = referral_group
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        group = get_model('dashboard', 'Group').objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.referral_partner_parent = referral_user
        temp_user.is_partner = True
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        referral_cut = get_model('dashboard', 'Cut').objects.create(group=referral_group, vendor=vendor, cut=0.7)
        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 2)
        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 4)

        sales = get_model('dashboard', 'Sale').objects.all()

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertTrue(sale.is_referral_sale)

        self.assertEqual(sale.referral_user, referral_user)
        self.assertEqual(sale.original_commission, 100)

        earnings = get_model('dashboard', 'UserEarning').objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'referral_sale_commission':
                self.assertEqual(earning.amount, 15.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 60.000)

        #Update sales status
        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(earning.status, get_model('dashboard', 'Sale').PENDING)

        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()

        earnings = get_model('dashboard', 'UserEarning').objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').CONFIRMED)

    def test_user_earning_apprl_direct_sale(self):
        """ Tests UserEarnings when a direct sales is generated on APPRL.com """
        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)
        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = ''
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        sale = get_model('dashboard', 'Sale').objects.get(vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 1)

        earning = get_model('dashboard', 'UserEarning').objects.all()[0]

        self.assertEqual(earning.user_earning_type, 'apprl_commission')
        self.assertEqual(earning.amount, 100)

    def test_commissions_publisher_network_with_exceptions(self):
        """ Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
            owner doesn't belong to a Publisher Network with cuts exceptions
        """
        group = get_model('dashboard', 'Group').objects.create(name='mygroup')

        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.partner_group = group
        owner_user.owner_network_cut = 0.5
        owner_user.save()

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        rules = [{"sid": temp_user.id, "cut": 1, "tribute": 0}]
        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2, rules_exceptions=rules)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 3)

        earnings = get_model('dashboard', 'UserEarning').objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 0.000)
            elif earning.user_earning_type == 'publisher_network_tribute':
                self.assertEqual(earning.amount, 0.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 100.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').PENDING)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()

        earnings = get_model('dashboard', 'UserEarning').objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').CONFIRMED)

    def test_commissions_recursive_publisher_network_with_exceptions(self):
        """ Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
        owner belongs to a Publisher Network recursively with cuts exceptions
        """
        group = get_model('dashboard', 'Group').objects.create(name='mygroup')

        master_owner = get_user_model().objects.create_user('master_owner', 'master_owner@xvid.se', 'master_owner')
        master_owner.owner_network_cut = 0.2
        master_owner.partner_group = group
        master_owner.save()

        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.5
        owner_user.partner_group = group
        owner_user.owner_network = master_owner
        owner_user.save()

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        rules = [{"sid": temp_user.id, "cut": 0.90, "tribute": 0.50}, {"sid": owner_user.id, "cut": 0.90, "tribute": 0.5}, {"sid": master_owner.id, "cut": 0.90, "tribute": 1}]
        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2, rules_exceptions=rules)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 4)

        earnings = get_model('dashboard', 'UserEarning').objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 10.000)
            elif earning.user_earning_type == 'publisher_sale_tribute' and earning.user == owner_user:
                self.assertEqual(earning.amount, 0.000)
            elif earning.user_earning_type == 'publisher_sale_tribute' and earning.user == master_owner:
                self.assertEqual(earning.amount, 45.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 45.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').PENDING)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()

        earnings = get_model('dashboard', 'UserEarning').objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').CONFIRMED)

    def test_user_earnings_same_publisher_and_owner(self):
        """ Tests UserEarnings that are generated when the publisher and the Publisher Network owner
            are the same user
        """
        group = get_model('dashboard', 'Group').objects.create(name='mygroup')

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network_cut = 0.1
        temp_user.owner_network = temp_user
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 2)

        earnings = get_model('dashboard', 'UserEarning').objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 60.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').PENDING)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()

        earnings = get_model('dashboard', 'UserEarning').objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').CONFIRMED)

    def test_user_earnings_same_owner_hierarchy(self):
        """ Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
            owner is has set itself as its owner
        """
        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.1
        owner_user.owner_network = owner_user
        owner_user.save()

        group = get_model('dashboard', 'Group').objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 3)

        earnings = get_model('dashboard', 'UserEarning').objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_network_tribute':
                self.assertEqual(earning.amount, 6.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 54.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').PENDING)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()

        earnings = get_model('dashboard', 'UserEarning').objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, get_model('dashboard', 'Sale').CONFIRMED)


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestAffiliateNetworks(TransactionTestCase):
    def setUp(self):
        FXRate = get_model('importer', 'FXRate')
        FXRate.objects.create(currency='SEK', base_currency='SEK', rate='1.00')
        FXRate.objects.create(currency='EUR', base_currency='SEK', rate='0.118160')
        FXRate.objects.create(currency='SEK', base_currency='EUR', rate='8.612600')
        FXRate.objects.create(currency='EUR', base_currency='EUR', rate='1.00')

        self.user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        self.user.location = 'SE'
        self.user.save()

        self.vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        self.boozt_se_vendor = get_model('apparel', 'Vendor').objects.create(name='Boozt se')
        self.boozt_no_vendor = get_model('apparel', 'Vendor').objects.create(name='Boozt no')

        for i in range(1, 10):
            get_model('apparel', 'Product').objects.create(sku=str(i))

    def test_linkshare_parser(self):
        text = open(os.path.join(settings.PROJECT_ROOT, 'test_files/linkshare_test.csv')).read()
        data = text.splitlines()
        management.call_command('dashboard_import', 'linkshare', data=data, verbosity=0, interactive=False)

        sale_model = get_model('dashboard', 'Sale')

        self.assertEqual(sale_model.objects.count(), 13)
        # Test one sale is generated if contains  multiple products
        sale = sale_model.objects.filter(original_sale_id='500953651').count()
        self.assertEqual(sale, 1)

        sale = sale_model.objects.get(original_sale_id='500953651')
        # Test when a sale is cancelled
        self.assertAlmostEqual(sale.original_amount, 0)
        self.assertAlmostEqual(sale.original_commission, 0)
        self.assertEqual(sale.status, sale_model.DECLINED)

        sale = sale_model.objects.get(original_sale_id='4105550')
        # Test products are being summarized in the sale
        self.assertAlmostEqual(sale.original_amount, decimal.Decimal('111.55'))
        self.assertAlmostEqual(sale.original_commission, decimal.Decimal('6.70'))
        self.assertGreater(sale.status, sale_model.PENDING)

        sale = sale_model.objects.get(original_sale_id='500873991')
        # Multiple products, all  were cancelled
        self.assertAlmostEqual(sale.original_amount, 0)
        self.assertAlmostEqual(sale.original_commission, 0)
        self.assertEqual(sale.status, sale_model.DECLINED)

        sale = sale_model.objects.get(original_sale_id='500864773')
        # Multiple products, some  were cancelled
        self.assertAlmostEqual(sale.original_amount, decimal.Decimal('150.55'))
        self.assertAlmostEqual(sale.original_commission, decimal.Decimal('9.03'))
        self.assertGreater(sale.status, sale_model.PENDING)

    def test_tradedoubler_boozt_parser(self):
        text = open(os.path.join(settings.PROJECT_ROOT, 'test_files/tradoubler_test.xml')).read()

        management.call_command('dashboard_import', 'tradedoubler', data=text, verbosity=0, interactive=False)

        sale_model = get_model('dashboard', 'Sale')

        self.assertEqual(sale_model.objects.filter(affiliate="Tradedoubler").count(), 7)

        boozt_se_sales = sale_model.objects.filter(vendor=self.boozt_se_vendor).count()
        self.assertEqual(boozt_se_sales, 2)

        boozt_no_sales = sale_model.objects.filter(vendor=self.boozt_no_vendor).count()
        self.assertEqual(boozt_no_sales, 5)


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestSalesPerClick(TransactionTestCase):
    fixtures = ['test-fxrates.yaml']

    def setUp(self):
        self.user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        self.user.is_partner = True
        self.user.save()
        self.group = get_model('dashboard', 'Group').objects.create(name='group_name')
        self.user.partner_group = self.group
        self.user.save()

        self.vendor = get_model('apparel', 'Vendor').objects.create(name='Vendor', is_cpc=True)
        self.other_vendor = get_model('apparel', 'Vendor').objects.create(name='Other vendor', is_cpc=True)

        get_model('dashboard', 'Cut').objects.create(cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, group=self.group,
                                                     vendor=self.vendor)
        get_model('dashboard', 'Cut').objects.create(cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, group=self.group,
                                                     vendor=self.other_vendor)

        category = get_model('apparel', 'Category').objects.create(name='Category')
        manufacturer = get_model('apparel', 'Brand').objects.create(name='Brand')
        self.product = get_model('apparel', 'Product').objects.create(
            product_name='Product',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True
        )
        self.product2 = get_model('apparel', 'Product').objects.create(
            product_name='Other Product',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True,
            sku=123
        )
        self.product3 = get_model('apparel', 'Product').objects.create(
            product_name='Other Product Number 3',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True,
            sku=456
        )
        get_model('apparel', 'VendorProduct').objects.create(product=self.product, vendor=self.vendor)
        get_model('apparel', 'VendorProduct').objects.create(product=self.product2, vendor=self.other_vendor)
        get_model('apparel', 'VendorProduct').objects.create(product=self.product3, vendor=self.vendor)
        get_model('dashboard', 'ClickCost').objects.create(vendor=self.vendor, amount=1.00, currency="EUR")
        get_model('dashboard', 'ClickCost').objects.create(vendor=self.other_vendor, amount=50.00, currency="SEK")

    def test_sale_cost_per_click(self):
        ''' Test that earnings per clicks are being generated
        '''
        ip = "192.128.2.3"
        yesterday = (datetime.date.today() - datetime.timedelta(1))

        for i in range(0, 100):
            get_model('statistics', 'ProductStat').objects.create(product=self.product.product_name, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.vendor.name,
                                                                  ip=ip, created=yesterday)
        #query_date = yesterday.strftime('%d-%m-%Y')
        management.call_command('clicks_summary', verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        self.assertEqual(get_model('dashboard', 'Sale').objects.get().amount, 100)

        click_cost = get_model('dashboard', 'ClickCost').objects.get(vendor=self.vendor)
        sale_amount = 100 * click_cost.amount

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 2)
        _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(self.user.id, self.vendor)
        earning_cut = normal_cut * publisher_cut

        user_earning = get_model('dashboard', 'UserEarning').objects.get(user=self.user)
        self.assertAlmostEqual(user_earning.amount, decimal.Decimal("%.2f" % (sale_amount * earning_cut)))

    def test_sale_cost_per_click_currency_exchange(self):
        """Test that earnings per clicks are being generated in EUR, even when the ClickCost is defined in another
        currency
        """
        ip = "192.128.2.3"
        yesterday = (datetime.date.today() - datetime.timedelta(1))

        # Generate random ProductStat data
        for i in range(0, 100):
            get_model('statistics', 'ProductStat').objects.create(product=self.product2.product_name, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.other_vendor.name,
                                                                  ip=ip, created=yesterday)
        management.call_command('clicks_summary', verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        click_cost = get_model('dashboard', 'ClickCost').objects.get(vendor=self.other_vendor)
        rate = currency_exchange('EUR', click_cost.currency)
        _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(self.user.id, self.other_vendor)
        earning_cut = normal_cut * publisher_cut
        sale_amount = 100 * click_cost.amount * rate
        self.assertEqual(get_model('dashboard', 'Sale').objects.get().converted_amount, sale_amount)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 2)

        user_earning = get_model('dashboard', 'UserEarning').objects.get(user=self.user)
        self.assertAlmostEqual(user_earning.amount, decimal.Decimal("%.2f" % (sale_amount * earning_cut)))

    def test_cost_per_clicks_historical_clicks(self):
        """Test that not clicks from today are being shown in the dashboard. This clicks can't be included until their
        respective earnings are generated
        """
        yesterday = (datetime.date.today() - datetime.timedelta(1))
        ip = "192.128.2.3"

        # Generated 100 clicks yesterday
        for i in range(0, 100):
            get_model('statistics', 'ProductStat').objects.create(product=self.product2.product_name, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.vendor.name,
                                                                  ip=ip, created=yesterday)
        # Generated 2000 clicks today
        for i in range(0, 2000):
            get_model('statistics', 'ProductStat').objects.create(product=self.product2.product_name, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.vendor.name,
                                                                  ip=ip)
        management.call_command('clicks_summary', verbosity=0, interactive=False)
        self.assertEqual(get_total_clicks_per_vendor(self.vendor), 100)

    #@unittest.skip("Review this test")
    def test_detail_clicks_amount(self):
        ''' Test that detailed data for clicks per day is being generated correctly
        '''
        yesterday = (datetime.date.today() - datetime.timedelta(1))
        ip = "192.128.2.3"
        for i in range(0, 52):
            get_model('statistics', 'ProductStat').objects.create(product=self.product.slug, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.vendor.name,
                                                                  ip=ip, created=yesterday)
        for i in range(0, 48):
            get_model('statistics', 'ProductStat').objects.create(product=self.product3.slug, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.vendor.name,
                                                                  ip=ip, created=yesterday)
        management.call_command('clicks_summary', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 2)
        user_earning = get_model('dashboard', 'UserEarning').objects.get(user=self.user)

        # Simulate a POST call for clicks detail
        dict_data = {'user_id': self.user.id, 'vendor': self.vendor.name, 'clicks': 100, 'amount': user_earning.amount,
                     'date': calendar.timegm(yesterday.timetuple())}
        response = self.client.get(reverse('clicks-detail'), dict_data,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        response_dict = json.loads(response.content)
        sum_clicks = 0
        for item in response_dict:
            self.assertEqual(item['user_id'], self.user.id)
            self.assertEqual(item['vendor'], self.vendor.name)
            sum_clicks += item['clicks']
        self.assertEqual(sum_clicks, 100)

    def test_sale_cost_per_click_apprl_clicks(self):
        ''' Test that earnings per clicks are being generated for clicks on apprl.com
        '''
        ip = "192.128.2.3"
        yesterday = (datetime.date.today() - datetime.timedelta(1))

        for i in range(0, 100):
            get_model('statistics', 'ProductStat').objects.create(product=self.product.product_name, page="BuyReferral",
                                                                  user_id=0, vendor=self.vendor.name,
                                                                  ip=ip, created=yesterday)
        management.call_command('clicks_summary', verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        click_cost = get_model('dashboard', 'ClickCost').objects.get(vendor=self.vendor)
        sale_amount = 100 * click_cost.amount
        self.assertEqual(get_model('dashboard', 'Sale').objects.get().amount, sale_amount)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 1)
        user_earning = get_model('dashboard', 'UserEarning').objects.get()
        self.assertEqual(user_earning.user_earning_type, 'apprl_commission')
        self.assertAlmostEqual(user_earning.amount, sale_amount)

@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestPayments(TransactionTestCase):

    def test_payments(self):
        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.1
        owner_user.save()

        payment_detail = get_model('profile', 'PaymentDetail').objects.create(name='a', company='b', orgnr='c', user=owner_user)

        group = get_model('dashboard', 'Group').objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        payment_detail = get_model('profile', 'PaymentDetail').objects.create(name='a', company='b', orgnr='c', user=temp_user)

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='5000', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 3)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)

        #Update a sales transaction
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()
        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 3)

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Payment').objects.count(), 2)

        publisher_payment = get_model('dashboard', 'Payment').objects.get(user=temp_user)
        self.assertEqual(publisher_payment.amount, 540)

        owner_payment = get_model('dashboard', 'Payment').objects.get(user=owner_user)
        self.assertEqual(owner_payment.amount, 60)

        for earning in get_model('dashboard', 'UserEarning').objects.exclude(user_earning_type='apprl_commission'):
            self.assertEqual(earning.paid, get_model('dashboard', 'Sale').PAID_READY)

        owner_set = get_model('dashboard', 'Payment').objects.filter(user=owner_user)

    def test_payments_referral_sale(self):
        referral_group = get_model('dashboard', 'Group').objects.create(name='mygroup')
        referral_user = get_user_model().objects.create_user('referral', 'referral@xvid.se', 'referral')
        referral_user.partner_group = referral_group
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        get_model('profile', 'PaymentDetail').objects.create(name='a', company='b', orgnr='c',
                                                                              user=referral_user)

        group = get_model('dashboard', 'Group').objects.create(name='mygroup')

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.referral_partner_parent = referral_user
        temp_user.is_partner = True
        temp_user.save()

        payment_detail = get_model('profile', 'PaymentDetail').objects.create(name='a', company='b', orgnr='c',
                                                                              user=temp_user)

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        referral_cut = get_model('dashboard', 'Cut').objects.create(group=referral_group, vendor=vendor, cut=0.7)
        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='5000', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 2)

        for sale in get_model('dashboard', 'Sale').objects.all():
            # Update a sales transaction
            sale.status = get_model('dashboard', 'Sale').CONFIRMED
            sale.save()

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Payment').objects.count(), 2)

        publisher_payment = get_model('dashboard', 'Payment').objects.get(user=temp_user)
        self.assertEqual(publisher_payment.amount, 620)

        referral_payment = get_model('dashboard', 'Payment').objects.get(user=referral_user)
        self.assertEqual(referral_payment.amount, 150)

    def test_payments_recursive_publisher_network(self):

        super_master_owner = get_user_model().objects.create_user('super_master_owner', 'super_master_owner@xvid.se', 'super_master_owner')
        super_master_owner.owner_network_cut = 0.5
        super_master_owner.save()

        master_owner = get_user_model().objects.create_user('master_owner', 'master_owner@xvid.se', 'master_owner')
        master_owner.owner_network_cut = 0.2
        master_owner.owner_network = super_master_owner
        master_owner.save()

        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.5
        owner_user.owner_network = master_owner
        owner_user.save()

        group = get_model('dashboard', 'Group').objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        get_model('profile', 'PaymentDetail').objects.create(name='a', company='b', orgnr='c',
                                                                              user=super_master_owner)
        get_model('profile', 'PaymentDetail').objects.create(name='a', company='b', orgnr='c',
                                                                                      user=master_owner)
        get_model('profile', 'PaymentDetail').objects.create(name='a', company='b', orgnr='c',
                                                                                      user=owner_user)
        get_model('profile', 'PaymentDetail').objects.create(name='a', company='b', orgnr='c',
                                                                                      user=temp_user)

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='5000', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 1000)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 5)

        for sale in get_model('dashboard', 'Sale').objects.all():
            # Update a sales transaction
            sale.status = get_model('dashboard', 'Sale').CONFIRMED
            sale.save()

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Payment').objects.count(), 2)

        publisher_payment = get_model('dashboard', 'Payment').objects.get(user=temp_user)
        self.assertEqual(publisher_payment.amount, 300)

        owner_payment = get_model('dashboard', 'Payment').objects.get(user=owner_user)
        self.assertEqual(owner_payment.amount, 240)

    def test_payments_user_earnings_history(self):
        group = get_model('dashboard', 'Group').objects.create(name='mygroup')

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)
        get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=1, referral_cut=0.2)
        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)

        counter = 10
        while counter > 0:
            response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
            self.assertEqual(response.status_code, 302)
            response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id=counter, order_value='5000', currency='EUR'))))
            self.assertEqual(response.status_code, 200)

            # Import the sale transaction
            management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
            counter -= 1

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 10)

        for sale in get_model('dashboard', 'Sale').objects.all():
            #Update a sales transaction
            self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
            sale.status = get_model('dashboard', 'Sale').CONFIRMED
            sale.save()

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Payment').objects.count(), 1)

        # The id of the earnings ready to pay are included in the earning field in the Payment instance
        earnings_ids_list = get_model('dashboard', 'UserEarning').objects.\
            filter(user=temp_user, status=Sale.CONFIRMED, paid=Sale.PAID_READY).values_list('id', flat=True)

        payment = get_model('dashboard', 'Payment').objects.get(user=temp_user, paid=False)
        items = json.loads(payment.earnings)

        for earning_id in items:
            self.assertIn(earning_id, earnings_ids_list)

        # The sum of the current earnings ready to pay is the same that the amount of the Payment
        total_query = get_model('dashboard', 'UserEarning').objects.\
            filter(user=temp_user, status=Sale.CONFIRMED, paid=Sale.PAID_READY).aggregate(Sum('amount'))

        self.assertEqual(payment.amount, total_query['amount__sum'])



@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory',
                   APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA='cache_aggregated_test')
class TestAggregatedData(TransactionTestCase):
    def setUp(self):
        self.owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        self.owner_user.owner_network_cut = 0.1
        self.owner_user.name = 'owner_user'
        self.owner_user.save()
        self.vendor = get_model('apparel', 'Vendor').objects.create(name='mystore')
        self.vendor_cpc = get_model('apparel', 'Vendor').objects.create(name='mystorecpc', is_cpc=True, is_cpo=False)
        self.group = get_model('dashboard', 'Group').objects.create(name='mygroup')
        self.cut = get_model('dashboard', 'Cut').objects.create(group=self.group, vendor=self.vendor, cut=0.6,
                                                                referral_cut=0.2)
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        self.store = get_model('advertiser', 'Store').objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=self.vendor)

        store_user_cpc = get_user_model().objects.create_user('storecpc', 'storecpc@xvid.se', 'store')
        self.storecpc = get_model('advertiser', 'Store').objects.create(identifier='mystorecpc',
                                                                user=store_user_cpc,
                                                                vendor=self.vendor_cpc)

        self.user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        self.user.partner_group = self.group
        self.user.name = 'user'
        self.user.owner_network = self.owner_user
        self.user.save()

        category = get_model('apparel', 'Category').objects.create(name='Category')
        manufacturer = get_model('apparel', 'Brand').objects.create(name='Brand')
        self.product = get_model('apparel', 'Product').objects.create(
            product_name='Product',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True
        )
        get_model('apparel', 'VendorProduct').objects.create(product=self.product, vendor=self.vendor_cpc)
        get_model('dashboard', 'ClickCost').objects.create(vendor=self.vendor_cpc, amount=1.00, currency="EUR")

    def test_aggregated_data(self):
        # Sale and User earnings must be created
        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (self.user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='5000', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 3)

        str_date = datetime.date.today().strftime('%Y-%m-%d')
        management.call_command('collect_aggregated_data', date=str_date, verbosity=0, interactive=False)

        # Check total aggregated data generated in total
        self.assertEqual(get_model('dashboard', 'AggregatedData').objects.count(), 4)

        # Check total aggregated data generated by type
        self.assertEqual(get_model('dashboard', 'AggregatedData').objects.filter(data_type="aggregated_from_total").
                         count(), 3)
        self.assertEqual(get_model('dashboard', 'AggregatedData').objects.filter(data_type="aggregated_from_publisher").
                         count(), 1)

        for data in get_model('dashboard', 'AggregatedData').objects.filter(data_type="aggregated_from_total"):
            if data.user_id == self.user.id:
                self.assertEqual(data.sale_earnings, decimal.Decimal(540))

            elif data.user_id == self.owner_user.id:
                self.assertEqual(data.network_sale_earnings, decimal.Decimal(60))
                self.assertEqual(data.network_click_earnings, decimal.Decimal(0))
            elif data.user_id == 0:
                self.assertEqual(data.user_name, 'APPRL')
                self.assertEqual(data.sale_earnings, decimal.Decimal(400))

    def test_update_aggregated_data(self):
        cache.set("COOKIE_TEST", 1)
        cache_data = cache.get("COOKIE_TEST")
        self.assertEqual(cache_data, 1)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (self.user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='5000', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

         # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        self.assertEqual(get_model('dashboard', 'UserEarning').objects.count(), 3)

        str_date = datetime.date.today().strftime('%Y-%m-%d')
        management.call_command('collect_aggregated_data', date=str_date, verbosity=0, interactive=False)

        # Check total aggregated data generated in total
        self.assertEqual(get_model('dashboard', 'AggregatedData').objects.count(), 4)

        # Check total aggregated data generated by type
        self.assertEqual(get_model('dashboard', 'AggregatedData').objects.filter(data_type="aggregated_from_total").
                         count(), 3)
        self.assertEqual(get_model('dashboard', 'AggregatedData').objects.filter(data_type="aggregated_from_publisher").
                         count(), 1)

        for data in get_model('dashboard', 'AggregatedData').objects.filter(data_type="aggregated_from_total"):
            if data.user_id == self.user.id:
                self.assertEqual(data.sale_earnings, decimal.Decimal(540))

            elif data.user_id == self.owner_user.id:
                self.assertEqual(data.network_sale_earnings, decimal.Decimal(60))
                self.assertEqual(data.network_click_earnings, decimal.Decimal(0))
            elif data.user_id == 0:
                self.assertEqual(data.user_name, 'APPRL')
                self.assertEqual(data.sale_earnings, decimal.Decimal(400))

        # Sale is canceled
        sale = get_model('dashboard', 'Sale').objects.all()[0]
        sale.status = get_model('dashboard', 'Sale').DECLINED
        sale.save()

        cache_data = cache.get(settings.APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA)
        self.assertNotEqual(cache_data, None)
        management.call_command('update_aggregated_data', verbosity=0, interactive=False)

        cache_data = cache.get(settings.APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA)
        self.assertEqual(cache_data, None)

        for data in get_model('dashboard', 'AggregatedData').objects.filter(data_type="aggregated_from_total"):
            if data.user_id == self.user.id:
                self.assertEqual(data.sale_earnings, decimal.Decimal(0))

            elif data.user_id == self.owner_user.id:
                self.assertEqual(data.network_sale_earnings, decimal.Decimal(0))
                self.assertEqual(data.network_click_earnings, decimal.Decimal(0))
            elif data.user_id == 0:
                self.assertEqual(data.user_name, 'APPRL')
                self.assertEqual(data.sale_earnings, decimal.Decimal(0))

class TestPaymentHistory(TestCase):

    def test_few_earnings_payments_history(self):
        user = UserFactory.create()
        vendor = VendorFactory.create()
        CutFactory.create(vendor=vendor, group=user.partner_group, cut=0.67)

        for index in range(1, 11):
            SaleFactory.create(user_id=user.id, vendor=vendor)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.filter(
            user_earning_type='publisher_sale_commission').count(), 10)

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Payment').objects.all().count(), 1)

        payment = get_model('dashboard', 'Payment').objects.all()[0]
        earnings_dict = json.loads(payment.earnings)

        earnings = get_model('dashboard', 'UserEarning').objects.filter(user_earning_type='publisher_sale_commission')
        for item in earnings:
            self.assertIn(item.id, earnings_dict)

    def test_multiple_earnings_payments_history(self):
        user = UserFactory.create()
        vendor = VendorFactory.create()
        CutFactory.create(vendor=vendor, group=user.partner_group, cut=0.67)

        for index in range(1, 101):
            SaleFactory.create(user_id=user.id, vendor=vendor)

        self.assertEqual(get_model('dashboard', 'UserEarning').objects.filter(
            user_earning_type='publisher_sale_commission').count(), 100)

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Payment').objects.all().count(), 1)
