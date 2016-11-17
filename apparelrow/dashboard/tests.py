import re
import urllib
import os
import logging
from decimal import Decimal as D
from django.contrib.admin import AdminSite

from advertiser.models import Transaction
from apparelrow.dashboard.factories import *

from django.core import mail
from django.core import signing
from django.core.urlresolvers import reverse as _reverse
from django.test import TransactionTestCase, TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.core import management
from django.conf import settings

from localeurl.utils import locale_url
from apparelrow.apparel.models import Vendor, Product, Brand, Category, VendorProduct, Location
from apparelrow.dashboard.models import Group, StoreCommission, Cut, Sale, UserEarning, Payment, Signup

from apparelrow.dashboard.utils import *
from apparelrow.dashboard.admin import SaleAdmin
from apparelrow.dashboard.views import get_store_earnings
from apparelrow.dashboard import stats_admin
from apparelrow.dashboard.stats_cache import stats_cache, mrange, flush_stats_cache, \
    flush_stats_cache_by_month, flush_stats_cache_by_year, redis as stats_redis, cache_key
from apparelrow.apparel.utils import generate_sid, parse_sid, currency_exchange,\
    SOURCE_LINK_MAX_LEN, compress_source_link_if_needed, links_redis_connection, links_redis_key
from apparelrow.dashboard.forms import SaleAdminFormCustom
from django.core.cache import cache

from apparelrow.importer.models import FXRate
from apparelrow.profile.models import PaymentDetail
from apparelrow.statistics.factories import *

from mock import patch
from model_mommy.mommy import make
from freezegun import freeze_time

from apparelrow.statistics.models import ProductStat


def reverse(*args, **kwargs):
    return locale_url(_reverse(*args, **kwargs), 'en')

def get_current_month_range():
    year = datetime.date.today().year
    month = datetime.date.today().month
    start_date, end_date = parse_date(month, year)
    return start_date, end_date


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestDashboard(TransactionTestCase):

    def setUp(self):
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

        instance = Signup.objects.get()
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

        instance = Signup.objects.get()
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
        # parent date and adds 50 EUR to the account
        registered_user.is_partner = True
        registered_user.save()
        self.assertIsNotNone(registered_user.referral_partner_parent_date)

        sale = Sale.objects.get(is_promo=True)
        self.assertFalse(sale.is_referral_sale)
        self.assertIsNone(sale.referral_user)
        self.assertTrue(sale.is_promo)
        self.assertEqual(sale.commission, decimal.Decimal(50))
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

        # Invalid referral link should not result in a promo sale of 50 EUR
        self.assertEqual(Sale.objects.count(), 0)

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

        self.assertEqual(Sale.objects.count(), 1)

        another_user = get_user_model().objects.create_user('another_user', 'another@xvid.se', 'another')
        another_user.referral_partner = True
        another_user.is_partner = True
        another_user.save()

        response = self.client.get(another_user.get_referral_url(), follow=True)
        response = self.client.get('/')

        registered_user = get_user_model().objects.get(email='test@xvid.se')
        self.assertEqual(registered_user.referral_partner_parent, referral_user)
        self.assertIsNotNone(registered_user.referral_partner_parent_date)

        self.assertEqual(Sale.objects.count(), 1)

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
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
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

        self.assertEqual(Sale.objects.count(), 2) # referral sale and referral signup

        # Verify it
        referral_signup_sale = Sale.objects.get(is_referral_sale=False)
        self.assertTrue(referral_signup_sale.is_promo)

        referral_user_sale = Sale.objects.get(is_promo=False)
        self.assertTrue(referral_user_sale.is_referral_sale)

        # This test
        #self.assertEqual(referral_user_sale.referral_user, referral_user)
        #self.assertEqual(referral_user_sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

        # Repeat the import of the sale transaction
        #management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        #self.assertEqual(Sale.objects.count(), 1)

        # Verify it
        #referral_user_sale = Sale.objects.get(is_promo=False, is_referral_sale=True)
        #self.assertTrue(referral_user_sale.is_referral_sale)
        #self.assertEqual(referral_user_sale.referral_user, referral_user)
        #self.assertEqual(referral_user_sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestDashboardCuts(TransactionTestCase):

    def setUp(self):
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
        vendor = Vendor.objects.create(name=store_id)
        store = Store.objects.create(identifier=store_id, user=store_user, commission_percentage='0.2', vendor=vendor)
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id=order_id, order_value=order_value, currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        return vendor, Transaction.objects.get(store_id=store_id, order_id=order_id)

    def test_default_cut(self):
        user = self._create_partner_user()
        vendor, transaction = self._create_transaction(user, order_value='500')
        self.assertTrue(vendor.is_cpo)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        # Verify sale transaction
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.get()
        self.assertEqual(sale.type, Sale.COST_PER_ORDER)
        self.assertIsNotNone(sale)
        self.assertEqual(sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

    def test_non_default_cut(self):
        user = self._create_partner_user()
        vendor, transaction = self._create_transaction(user, order_value='500')
        self.assertTrue(vendor.is_cpo)

        # Create group + cut for store vendor
        group = Group.objects.create(name='group_name')
        cuts = Cut.objects.create(vendor=vendor, group=group, cut='0.9')
        user.partner_group = group
        user.save()

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        # Verify sale transaction
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.get()
        self.assertEqual(sale.type, Sale.COST_PER_ORDER)
        self.assertIsNotNone(sale)
        self.assertEqual(sale.commission, decimal.Decimal(100) * decimal.Decimal('0.9'))

    def test_update_cut(self):
        user = self._create_partner_user()
        vendor, transaction = self._create_transaction(user, order_value='500')
        self.assertTrue(vendor.is_cpo)

        # Create group + cut for store vendor
        group = Group.objects.create(name='group_name')
        cuts = Cut.objects.create(vendor=vendor, group=group, cut='0.8')
        user.partner_group = group
        user.save()

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        # Verify sale transaction
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.get()
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
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.get()
        self.assertIsNotNone(sale)
        self.assertEqual(sale.commission, decimal.Decimal(100) * decimal.Decimal('0.8'))
        self.assertEqual(sale.cut, decimal.Decimal('0.8'))

    def test_do_not_update_after_paid_ready_status(self):
        user = self._create_partner_user()
        payment_detail = PaymentDetail.objects.create(name='a', company='b', orgnr='c', user=user)
        vendor, transaction = self._create_transaction(user, order_value='1000')
        self.assertTrue(vendor.is_cpo)

        group = Group.objects.create(name='mygroup')
        cut = Cut.objects.create(group=group, vendor=vendor, cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, referral_cut=0.2)

        user.partner_group = group
        user.save()

        # 1. Import the sale transaction and verify it
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.get()
        self.assertEqual(sale.type, Sale.COST_PER_ORDER)
        self.assertEqual(sale.commission, decimal.Decimal(200) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))
        self.assertEqual(sale.status, Sale.PENDING)
        self.assertEqual(sale.paid, Sale.PAID_PENDING)

        # Set transaction as accepted
        transaction = Transaction.objects.get()
        transaction.status = Transaction.ACCEPTED
        transaction.save()

        # 2. Import the sale transaction again and verify it
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.get()
        self.assertEqual(sale.commission, decimal.Decimal(200) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))
        self.assertEqual(sale.status, Sale.CONFIRMED)
        self.assertEqual(sale.paid, Sale.PAID_PENDING)

        # Update commission after the sale transaction has been marked as ready for payment
        transaction = Transaction.objects.get()
        transaction.order_value = decimal.Decimal('2000')
        transaction.commission = decimal.Decimal('400')
        transaction.save()

        # 3. Import the sale transaction again and verify it
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.get()
        #self.assertEqual(sale.commission, decimal.Decimal(400) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))
        self.assertEqual(sale.status, Sale.CONFIRMED)
        self.assertEqual(sale.paid, Sale.PAID_PENDING)

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        # Update commission after the sale transaction has been marked as ready for payment
        transaction = Transaction.objects.get()
        transaction.order_value = decimal.Decimal('500')
        transaction.commission = decimal.Decimal('100')
        transaction.save()

        self.assertEqual(UserEarning.objects.count(), 2)

        # 4. Import the sale transaction again and verify it
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.get()
        #self.assertEqual(sale.commission, decimal.Decimal(400) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))
        for earning in sale.userearning_set.all():
            self.assertEqual(earning.status, Sale.CONFIRMED)
            if earning.user_earning_type == "publisher_sale_commission":
                self.assertEqual(earning.paid, Sale.PAID_READY)
            if earning.user_earning_type == "apprl_commission":
                self.assertEqual(earning.paid, Sale.PAID_PENDING)

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
        vendor = Vendor.objects.create(name='vendor_name')
        group = Group.objects.create(name='group_name')
        cuts = Cut.objects.create(vendor=vendor, group=group, cut='0.5', referral_cut='0.3')
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

        group = Group.objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(UserEarning.objects.count(), 3)

        earnings = UserEarning.objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_network_tribute':
                self.assertEqual(earning.amount, 6.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 54.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, Sale.PENDING)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, Sale.PENDING)
        sale.status = Sale.CONFIRMED
        sale.save()

        earnings = UserEarning.objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, Sale.CONFIRMED)

    def test_user_earnings_no_publisher_network(self):
        """ Tests UserEarnings that are generated when the user doesn't belong to a Publisher Network """
        group = Group.objects.create(name='mygroup')

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(UserEarning.objects.count(), 2)

        earnings = UserEarning.objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 60.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, Sale.PENDING)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, Sale.PENDING)
        sale.status = Sale.CONFIRMED
        sale.save()

        earnings = UserEarning.objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, Sale.CONFIRMED)

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

        group = Group.objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(UserEarning.objects.count(), 5)

        earnings = UserEarning.objects.all()

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
            self.assertEqual(earning.status, Sale.PENDING)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, Sale.PENDING)
        sale.status = Sale.CONFIRMED
        sale.save()

        earnings = UserEarning.objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, Sale.CONFIRMED)

    def test_user_earnings_no_commission_group(self):
        """ Tests UserEarnings when user doesn't belong to a Commission Group """
        # User has no Commission Group assigned
        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
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
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(UserEarning.objects.count(), 0)

        # Create a group and assign it to user
        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.5
        owner_user.save()
        group = Group.objects.create(name='mygroup', owner=owner_user)
        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        temp_user.partner_group = group
        temp_user.save()

        # Update Sale status
        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, Sale.PENDING)
        sale.status = Sale.CONFIRMED
        sale.save()

        self.assertEqual(UserEarning.objects.count(), 2)
        earnings = UserEarning.objects.all()

        for earning in earnings:
            self.assertEqual(earning.status, Sale.CONFIRMED)
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 60.000)

    def test_user_earnings_referral_sale(self):
        """ Tests UserEarnings when a referral Sale is made """
        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.5
        owner_user.save()

        referral_group = Group.objects.create(name='mygroup', owner=owner_user)

        referral_user = get_user_model().objects.create_user('referral', 'referral@xvid.se', 'referral')
        referral_user.partner_group = referral_group
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        group = Group.objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.referral_partner_parent = referral_user
        temp_user.is_partner = True
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        referral_cut = Cut.objects.create(group=referral_group, vendor=vendor, cut=0.7)
        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)
        store = Store.objects.create(identifier='mystore',
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

        self.assertEqual(Sale.objects.count(), 2)
        self.assertEqual(UserEarning.objects.count(), 4)

        sales = Sale.objects.all()

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertTrue(sale.is_referral_sale)

        self.assertEqual(sale.referral_user, referral_user)
        self.assertEqual(sale.original_commission, 100)

        earnings = UserEarning.objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'referral_sale_commission':
                self.assertEqual(earning.amount, 15.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 60.000)

        #Update sales status
        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(earning.status, Sale.PENDING)

        self.assertEqual(sale.status, Sale.PENDING)
        sale.status = Sale.CONFIRMED
        sale.save()

        earnings = UserEarning.objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, Sale.CONFIRMED)

    def test_user_earning_apprl_direct_sale(self):
        """ Tests UserEarnings when a direct sales is generated on APPRL.com """
        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
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

        self.assertEqual(Sale.objects.count(), 1)

        sale = Sale.objects.get(vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(UserEarning.objects.count(), 1)

        earning = UserEarning.objects.all()[0]

        self.assertEqual(earning.user_earning_type, 'apprl_commission')
        self.assertEqual(earning.amount, 100)

    def test_commissions_publisher_network_with_exceptions(self):
        """ Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
            owner doesn't belong to a Publisher Network with cuts exceptions
        """
        group = Group.objects.create(name='mygroup')

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
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        rules = [{"sid": temp_user.id, "cut": 1, "tribute": 0}]
        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2, rules_exceptions=rules)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(UserEarning.objects.count(), 3)

        earnings = UserEarning.objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 0.000)
            elif earning.user_earning_type == 'publisher_network_tribute':
                self.assertEqual(earning.amount, 0.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 100.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, Sale.PENDING)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, Sale.PENDING)
        sale.status = Sale.CONFIRMED
        sale.save()

        earnings = UserEarning.objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, Sale.CONFIRMED)

    def test_commissions_recursive_publisher_network_with_exceptions(self):
        """ Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
        owner belongs to a Publisher Network recursively with cuts exceptions
        """
        group = Group.objects.create(name='mygroup')

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
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        rules = [{"sid": temp_user.id, "cut": 0.90, "tribute": 0.50}, {"sid": owner_user.id, "cut": 0.90, "tribute": 0.5}, {"sid": master_owner.id, "cut": 0.90, "tribute": 1}]
        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2, rules_exceptions=rules)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(UserEarning.objects.count(), 4)

        earnings = UserEarning.objects.all()

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
            self.assertEqual(earning.status, Sale.PENDING)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, Sale.PENDING)
        sale.status = Sale.CONFIRMED
        sale.save()

        earnings = UserEarning.objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, Sale.CONFIRMED)

    def test_user_earnings_same_publisher_and_owner(self):
        """ Tests UserEarnings that are generated when the publisher and the Publisher Network owner
            are the same user
        """
        group = Group.objects.create(name='mygroup')

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network_cut = 0.1
        temp_user.owner_network = temp_user
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.converted_commission, 100)

        earnings = UserEarning.objects.all()
        self.assertEqual(len(earnings), 2)

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 60.000)

        for earning in earnings:
            self.assertEqual(earning.status, Sale.PENDING)


        # If we update the Sale transaction when it is still pending, we should get new
        # UserEarnings
        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, Sale.PENDING)
        sale.converted_commission = 200
        sale.save()


        # the new user earnings should have new amounts since the Sale commision changed
        for earning in sale.userearning_set.all():
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 80.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 120.000)


        sale.status = Sale.CONFIRMED
        sale.save()


        # If we update the Sale transaction when it is confirmed, we should not get new earnings
        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        sale.converted_commission = 100
        sale.save()

        # the user earnings should stay the same
        for earning in sale.userearning_set.all():
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 80.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 120.000)

            self.assertEqual(earning.status, Sale.CONFIRMED)


    def test_user_earnings_same_owner_hierarchy(self):
        """ Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
            owner is has set itself as its owner
        """
        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.1
        owner_user.owner_network = owner_user
        owner_user.save()

        group = Group.objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 100)

        self.assertEqual(UserEarning.objects.count(), 3)

        earnings = UserEarning.objects.all()

        for earning in earnings:
            if earning.user_earning_type == 'apprl_commission':
                self.assertEqual(earning.amount, 40.000)
            elif earning.user_earning_type == 'publisher_network_tribute':
                self.assertEqual(earning.amount, 6.000)
            elif earning.user_earning_type == 'publisher_sale_commission':
                self.assertEqual(earning.amount, 54.000)

        #Update a sales transaction
        for earning in earnings:
            self.assertEqual(earning.status, Sale.PENDING)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.status, Sale.PENDING)
        sale.status = Sale.CONFIRMED
        sale.save()

        earnings = UserEarning.objects.all()
        for earning in earnings:
            self.assertEqual(earning.status, Sale.CONFIRMED)

    def get_cut_exception(self):
        cut_user = UserFactory.create()
        rules = [{"sid": cut_user.id, "cut": 0.97, "tribute": 0, click_cost:"10 SEK"}]
        cut_exception, publisher_cut_exception, click_cost = parse_rules_exception(rules, cut_user.id)
        self.assertEqual(click_cost, "10 SEK")
        self.assertEqual(cut_exception, 0.97)
        self.assertEqual(publisher_cut_exception, 1)

    def get_cut_exception_no_rules_exception(self):
        cut_user = UserFactory.create()
        rules = []
        cut_exception, publisher_cut_exception, click_cost = parse_rules_exception(rules, cut_user.id)
        self.assertIsNone(click_cost)
        self.assertIsNone(cut_exception)
        self.assertIsNone(publisher_cut_exception)


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestAffiliateNetworks(TransactionTestCase):
    def setUp(self):
        FXRate.objects.create(currency='SEK', base_currency='SEK', rate='1.00')
        FXRate.objects.create(currency='EUR', base_currency='SEK', rate='0.118160')
        FXRate.objects.create(currency='SEK', base_currency='EUR', rate='8.612600')
        FXRate.objects.create(currency='EUR', base_currency='EUR', rate='1.00')

        self.user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        self.user.location = 'SE'
        self.user.save()

        self.vendor = Vendor.objects.create(name='mystore')
        self.boozt_se_vendor = Vendor.objects.create(name='Boozt se')
        self.boozt_no_vendor = Vendor.objects.create(name='Boozt no')

        for i in range(1, 10):
            Product.objects.create(sku=str(i))

    def test_linkshare_parser(self):
        text = open(os.path.join(settings.PROJECT_ROOT, 'test_files/linkshare_test.csv')).read()
        data = text.splitlines()
        management.call_command('dashboard_import', 'linkshare', data=data, verbosity=0, interactive=False)

        sale_model = Sale

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

        sale_model = Sale

        self.assertEqual(sale_model.objects.filter(affiliate="Tradedoubler").count(), 7)

        boozt_se_sales = sale_model.objects.filter(vendor=self.boozt_se_vendor).count()
        self.assertEqual(boozt_se_sales, 2)

        boozt_no_sales = sale_model.objects.filter(vendor=self.boozt_no_vendor).count()
        self.assertEqual(boozt_no_sales, 5)

    def test_dashboard_links(self):
        text = open(os.path.join(settings.PROJECT_ROOT, 'test_files/linkshare_test.csv')).read()
        data = text.splitlines()
        management.call_command('dashboard_import', 'linkshare', data=data, verbosity=0, interactive=False)

        sale_model = Sale

        self.assertEqual(sale_model.objects.count(), 13)
        self.assertEqual(sale_model.objects.exclude(source_link__exact='').count(), 3)

        links_sales = sale_model.objects.exclude(source_link__exact='')
        for item in links_sales:
            self.assertEqual(item.source_link, 'http://www.mystore.com/shop/woman/shoes')


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestSalesPerClick(TransactionTestCase):
    fixtures = ['test-fxrates.yaml']

    def setUp(self):
        self.user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        self.user.is_partner = True
        self.user.save()
        self.group = Group.objects.create(name='group_name')
        self.user.partner_group = self.group
        self.user.save()

        self.vendor = Vendor.objects.create(name='Vendor', is_cpc=True)
        self.other_vendor = Vendor.objects.create(name='Other vendor', is_cpc=True)

        Cut.objects.create(cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, group=self.group,
                                                     vendor=self.vendor)
        Cut.objects.create(cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, group=self.group,
                                                     vendor=self.other_vendor)

        category = Category.objects.create(name='Category')
        manufacturer = Brand.objects.create(name='Brand')
        self.product = Product.objects.create(
            product_name='Product',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True
        )
        self.product2 = Product.objects.create(
            product_name='Other Product',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True,
            sku=123
        )
        self.product3 = Product.objects.create(
            product_name='Other Product Number 3',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True,
            sku=456
        )
        VendorProduct.objects.create(product=self.product, vendor=self.vendor)
        VendorProduct.objects.create(product=self.product2, vendor=self.other_vendor)
        VendorProduct.objects.create(product=self.product3, vendor=self.vendor)
        ClickCost.objects.create(vendor=self.vendor, amount=1.00, currency="EUR")
        ClickCost.objects.create(vendor=self.other_vendor, amount=50.00, currency="SEK")

    def test_sale_cost_per_click(self):
        ''' Test that earnings per clicks are being generated
        '''
        ip = "192.128.2.3"
        yesterday = (datetime.date.today() - datetime.timedelta(1))

        for i in range(0, 100):
            ProductStat.objects.create(product=self.product.product_name, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.vendor.name,
                                                                  ip=ip, created=yesterday)
        management.call_command('clicks_summary', verbosity=0, interactive=False)
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(Sale.objects.get().amount, 100)

        click_cost = ClickCost.objects.get(vendor=self.vendor)
        sale_amount = 100 * click_cost.amount

        self.assertEqual(UserEarning.objects.count(), 2)
        _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(self.user.id, self.vendor)
        earning_cut = normal_cut * publisher_cut

        user_earning = UserEarning.objects.get(user=self.user)
        self.assertAlmostEqual(user_earning.amount, decimal.Decimal("%.2f" % (sale_amount * earning_cut)))

    def test_sale_cost_per_click_currency_exchange(self):
        """Test that earnings per clicks are being generated in EUR, even when the ClickCost is defined in another
        currency
        """
        ip = "192.128.2.3"
        yesterday = (datetime.date.today() - datetime.timedelta(1))

        # Generate random ProductStat data
        for i in range(0, 100):
            ProductStat.objects.create(product=self.product2.product_name, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.other_vendor.name,
                                                                  ip=ip, created=yesterday)
        management.call_command('clicks_summary', verbosity=0, interactive=False)
        self.assertEqual(Sale.objects.count(), 1)

        click_cost = ClickCost.objects.get(vendor=self.other_vendor)
        rate = currency_exchange('EUR', click_cost.currency)
        _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(self.user.id, self.other_vendor)
        earning_cut = normal_cut * publisher_cut
        sale_amount = 100 * click_cost.amount * rate
        self.assertEqual(Sale.objects.get().converted_amount, sale_amount)

        self.assertEqual(UserEarning.objects.count(), 2)

        user_earning = UserEarning.objects.get(user=self.user)
        self.assertAlmostEqual(user_earning.amount, decimal.Decimal("%.2f" % (sale_amount * earning_cut)))

    def test_cost_per_clicks_historical_clicks(self):
        """Test that not clicks from today are being shown in the dashboard. This clicks can't be included until their
        respective earnings are generated
        """
        yesterday = (datetime.date.today() - datetime.timedelta(1))
        ip = "192.128.2.3"

        # Generated 100 clicks yesterday
        for i in range(0, 100):
            ProductStat.objects.create(product=self.product2.product_name, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.vendor.name,
                                                                  ip=ip, created=yesterday)
        # Generated 2000 clicks today
        for i in range(0, 2000):
            ProductStat.objects.create(product=self.product2.product_name, page="BuyReferral",
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
            ProductStat.objects.create(product=self.product.slug, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.vendor.name,
                                                                  ip=ip, created=yesterday)
        for i in range(0, 48):
            ProductStat.objects.create(product=self.product3.slug, page="BuyReferral",
                                                                  user_id=self.user.id, vendor=self.vendor.name,
                                                                  ip=ip, created=yesterday)
        management.call_command('clicks_summary', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)

        self.assertEqual(UserEarning.objects.count(), 2)
        user_earning = UserEarning.objects.get(user=self.user)

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
            ProductStat.objects.create(product=self.product.product_name, page="BuyReferral",
                                                                  user_id=0, vendor=self.vendor.name,
                                                                  ip=ip, created=yesterday)
        management.call_command('clicks_summary', verbosity=0, interactive=False)
        self.assertEqual(Sale.objects.count(), 1)

        click_cost = ClickCost.objects.get(vendor=self.vendor)
        sale_amount = 100 * click_cost.amount
        self.assertEqual(Sale.objects.get().amount, sale_amount)

        self.assertEqual(UserEarning.objects.count(), 1)
        user_earning = UserEarning.objects.get()
        self.assertEqual(user_earning.user_earning_type, 'apprl_commission')
        self.assertAlmostEqual(user_earning.amount, sale_amount)


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestSalesPerClickAllStores(TransactionTestCase):

    def setUp(self):
        group = GroupFactory.create(name='Metro Mode', has_cpc_all_stores=True)
        self.user = UserFactory.create(username="normal_user", email="normal@xvid.se", name="normal", is_partner=True,
                                       partner_group=group)
        self.vendor = VendorFactory.create(name="Vendor CPC", is_cpc=True, is_cpo=False)
        CutFactory.create(vendor=self.vendor, group=group, cpc_amount=3.00, cpc_currency="EUR", cut=0)
        ClickCostFactory.create(vendor=self.vendor, amount=10, currency="EUR")

        self.product = ProductFactory.create(slug="product")
        self.product_cpo = ProductFactory.create(slug="product_cpo")
        VendorProductFactory.create(vendor=self.vendor, product=self.product)

    def test_sales_per_click_all_stores(self):
        """
        Test user earnings and sales are creating correctly when a user belongs to a Commission Group that pays
        all its publishers per click for all stores.
        """
        yesterday = (datetime.date.today() - datetime.timedelta(1))

        clicks = 4
        for i in range(clicks):
            product_stat = ProductStatFactory.create(ip="1.2.3.4", vendor=self.vendor.name, product=self.product.slug,
                                                     user_id=self.user.id, created=yesterday)
            self.assertTrue(product_stat.is_valid)

        # Run job that generates sales from the summarized clicks from yesterday for user and vendor
        management.call_command('clicks_summary', verbosity=0, interactive=False)

        # It must have generated 2 sales, one regular click sale where APPRL gets 100% of the commission according to
        # Click cost defined, and another sale where Publisher gets 100% of commission according to the cost defined in
        # the Cut object.
        self.assertEqual(Sale.objects.count(), 2)

        # It must have generated 4 earnings, 2 of them would have the 100% of the commission for APPRL and the
        # publisher, respectively. The other two it must have commission equals to 0 for both mentioned sides.
        self.assertEqual(UserEarning.objects.count(), 4)

        self.assertEqual(UserEarning.objects.filter(user_earning_type="publisher_sale_click_commission").count(), 1)
        self.assertEqual(UserEarning.objects.filter(user_earning_type="apprl_commission").count(), 2)
        self.assertEqual(UserEarning.objects.filter(user_earning_type="publisher_sale_click_commission_all_stores").count(), 1)

        sale_cpc = Sale.objects.get(affiliate="cost_per_click")
        sale_cpc_all = Sale.objects.get(affiliate="cpc_all_stores")

        # All User earnings might have been created with the right user earning type and amount
        for row in UserEarning.objects.all():
            if row.user_earning_type == "publisher_sale_click_commission":
                self.assertEqual(row.amount, 0.00)
                self.assertEqual(row.user, self.user)
            elif row.user_earning_type == "publisher_sale_click_commission_all_stores":
                self.assertEqual(row.amount, 12.00)
                self.assertEqual(row.user, self.user)
            elif row.user_earning_type == "apprl_commission":
                if row.sale == sale_cpc:
                    self.assertEqual(row.amount, 40.00)
                elif row.sale == sale_cpc_all:
                    self.assertEqual(row.amount, 0.00)

        # Run job that aggregates data
        management.call_command('collect_aggregated_data', verbosity=0, interactive=False)

        # Check right amount of AggregatedData instances have been created
        self.assertEqual(AggregatedData.objects.count(), 3)

        for row in AggregatedData.objects.all():
            if row.data_type == "aggregated_from_total":
                if row.user_id == self.user.id:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, 12.00)
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, 0.00)
                    self.assertEqual(row.sale_plus_click_earnings, 12.00)
                    self.assertEqual(row.total_network_earnings, 0.00)
                    self.assertEqual(row.total_clicks, 4)
                    self.assertEqual(row.paid_clicks, 4)
                elif row.user_id == 0:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, 40.00)
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, 0.00)
                    self.assertEqual(row.sale_plus_click_earnings, 40.00)
                    self.assertEqual(row.total_network_earnings, 0.00)
                    self.assertEqual(row.total_clicks, 0)
                    self.assertEqual(row.paid_clicks, 4)
            elif row.data_type == "aggregated_from_product":
                if row.user_id == self.user.id:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, 12.00)
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, 0.00)
                    self.assertEqual(row.sale_plus_click_earnings, 12.00)
                    self.assertEqual(row.total_network_earnings, 0.00)
                    self.assertEqual(row.total_clicks, 4)
                    self.assertEqual(row.paid_clicks, 4)

    def test_sales_per_click_all_stores_with_network_owner(self):
        """
        Test user earnings and sales are creating correctly when a user belongs to a Commission Group that pays
        all its publishers per click for all stores and has assigned a Publisher network owner with its respective
        owner cut
        """
        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.1
        owner_user.save()

        self.user.owner_network = owner_user
        self.user.save()

        yesterday = (datetime.date.today() - datetime.timedelta(1))

        clicks = 4
        for i in range(clicks):
            product_stat = ProductStatFactory.create(ip="1.2.3.4", vendor=self.vendor.name, product=self.product.slug,
                                                     user_id=self.user.id, created=yesterday)
            self.assertTrue(product_stat.is_valid)

        # Run job that generates sales from the summarized clicks from yesterday for user and vendor
        management.call_command('clicks_summary', verbosity=0, interactive=False)

        # It must have generated 2 sales, one regular click sale where APPRL gets 100% of the commission according to
        # Click cost defined, and another sale where Publisher gets 100% of commission according to the cost defined in
        # the Cut object.
        self.assertEqual(Sale.objects.count(), 2)

        # It must have generated 4 earnings, 2 of them would have the 100% of the commission for APPRL and the
        # publisher, respectively. The other two it must have commission equals to 0 for both mentioned sides.
        self.assertEqual(UserEarning.objects.count(), 6)

        self.assertEqual(UserEarning.objects.filter(user_earning_type="publisher_sale_click_commission").count(), 1)
        self.assertEqual(UserEarning.objects.filter(user_earning_type="publisher_network_click_tribute").count(), 1)
        self.assertEqual(UserEarning.objects.filter(user_earning_type="apprl_commission").count(), 2)
        self.assertEqual(UserEarning.objects.filter(user_earning_type="publisher_sale_click_commission_all_stores").count(), 1)
        self.assertEqual(UserEarning.objects.filter(user_earning_type="publisher_network_click_tribute_all_stores").count(), 1)

        sale_cpc = Sale.objects.get(affiliate="cost_per_click")
        sale_cpc_all = Sale.objects.get(affiliate="cpc_all_stores")

        # All User earnings might have been created with the right user earning type and amount
        for row in UserEarning.objects.all():
            if row.user_earning_type == "publisher_sale_click_commission":
                self.assertEqual(row.amount, 0.00)
                self.assertEqual(row.user, self.user)
            elif row.user_earning_type == "publisher_sale_click_commission_all_stores":
                self.assertEqual(row.amount, decimal.Decimal("10.80"))
                self.assertEqual(row.user, self.user)
            elif row.user_earning_type == "publisher_network_click_tribute":
                self.assertEqual(row.amount, 0.00)
                self.assertEqual(row.user, self.user.owner_network)
            elif row.user_earning_type == "publisher_network_click_tribute_all_stores":
                self.assertEqual(row.amount, decimal.Decimal("1.20"))
                self.assertEqual(row.user, self.user.owner_network)
            elif row.user_earning_type == "apprl_commission":
                if row.sale == sale_cpc:
                    self.assertEqual(row.amount, 40.00)
                elif row.sale == sale_cpc_all:
                    self.assertEqual(row.amount, 0.00)

        # Run job that aggregates data
        management.call_command('collect_aggregated_data', verbosity=0, interactive=False)

        # Check right amount of AggregatedData instances have been created
        self.assertEqual(AggregatedData.objects.count(), 6)

        for row in AggregatedData.objects.all():
            if row.data_type == "aggregated_from_total":
                if row.user_id == self.user.id:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, decimal.Decimal("10.80"))
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, 0.00)
                    self.assertEqual(row.sale_plus_click_earnings, decimal.Decimal("10.80"))
                    self.assertEqual(row.total_network_earnings, 0.00)
                    self.assertEqual(row.total_clicks, 4)
                    self.assertEqual(row.paid_clicks, 4)
                elif row.user_id == owner_user.id:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, 0.00)
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, decimal.Decimal("1.20"))
                    self.assertEqual(row.sale_plus_click_earnings, 0.00)
                    self.assertEqual(row.total_network_earnings, decimal.Decimal("1.20"))
                    self.assertEqual(row.total_clicks, 0)
                    self.assertEqual(row.paid_clicks, 0)
                elif row.user_id == 0:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, 40.00)
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, 0.00)
                    self.assertEqual(row.sale_plus_click_earnings, 40.00)
                    self.assertEqual(row.total_network_earnings, 0.00)
                    self.assertEqual(row.total_clicks, 0)
                    self.assertEqual(row.paid_clicks, 4)
            elif row.data_type == "aggregated_from_product":
                if row.user_id == self.user.id:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, decimal.Decimal("10.80"))
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, 0.00)
                    self.assertEqual(row.sale_plus_click_earnings, decimal.Decimal("10.80"))
                    self.assertEqual(row.total_network_earnings, 0.00)
                    self.assertEqual(row.total_clicks, 4)
                    self.assertEqual(row.paid_clicks, 4)
                elif row.user_id == owner_user.id:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, 0.00)
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, decimal.Decimal("1.20"))
                    self.assertEqual(row.sale_plus_click_earnings, 0.00)
                    self.assertEqual(row.total_network_earnings, decimal.Decimal("1.20"))
                    self.assertEqual(row.total_clicks, 0)
                    self.assertEqual(row.paid_clicks, 0)
            elif row.data_type == "aggregated_from_publisher":
                self.assertEqual(row.user_id, owner_user.id)
                self.assertEqual(row.aggregated_from_id, self.user.id)
                self.assertEqual(row.sale_earnings, 0.00)
                self.assertEqual(row.click_earnings, decimal.Decimal("10.80"))
                self.assertEqual(row.referral_earnings, 0.00)
                self.assertEqual(row.network_sale_earnings, 0.00)
                self.assertEqual(row.network_click_earnings, decimal.Decimal("1.20"))
                self.assertEqual(row.sale_plus_click_earnings, decimal.Decimal("10.80"))
                self.assertEqual(row.total_network_earnings, decimal.Decimal("1.20"))
                self.assertEqual(row.total_clicks, 4)
                self.assertEqual(row.paid_clicks, 4)

    @patch('apparelrow.dashboard.tests.TestSalesPerClickAllStores.test_sales_per_click_all_stores_no_cut')
    def test_sales_per_click_all_stores_no_cut(self, mock_logger):
        """
        Test user earnings and sales are not correctly created when a user belongs to a Commission Group that pays
        all its publishers per click for all stores but there is not a cut created for this commission group and vendor.
        """
        group = GroupFactory.create(name='Group', has_cpc_all_stores=True)
        self.user.partner_group = group
        self.user.save()

        yesterday = (datetime.date.today() - datetime.timedelta(1))

        clicks = 4
        for i in range(clicks):
            product_stat = ProductStatFactory.create(ip="1.2.3.4", vendor=self.vendor.name, product=self.product.slug,
                                                     user_id=self.user.id, created=yesterday)
            self.assertTrue(product_stat.is_valid)

        # Run job that generates sales from the summarized clicks from yesterday for user and vendor
        management.call_command('clicks_summary', verbosity=0, interactive=False)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(UserEarning.objects.count(), 0)

        # Error will be log, so the error must be fixed. It will create user earnings once error is fixed but it is
        # recommended to run clicks_summary for the regarding date again
        mock_logger.warning('Cut for vendor %s and commission group for user %s does not exist' % (self.vendor.id, self.user.id))

        # Run job that aggregates data
        management.call_command('collect_aggregated_data', verbosity=0, interactive=False)

        # Check no AggregatedData instances have been created
        self.assertEqual(AggregatedData.objects.count(), 2)

        for row in AggregatedData.objects.all():
            if row.data_type == "aggregated_from_total":
                if row.user_id == self.user.id:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, 0.00)
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, 0.00)
                    self.assertEqual(row.sale_plus_click_earnings, 0.00)
                    self.assertEqual(row.total_network_earnings, 0.00)
                    self.assertEqual(row.total_clicks, 4)
                    self.assertEqual(row.paid_clicks, 0)
            elif row.data_type == "aggregated_from_product":
                self.assertEqual(row.user_id, row.user_id)
                self.assertEqual(row.sale_earnings, 0.00)
                self.assertEqual(row.click_earnings, 0.00)
                self.assertEqual(row.referral_earnings, 0.00)
                self.assertEqual(row.network_sale_earnings, 0.00)
                self.assertEqual(row.network_click_earnings, 0.00)
                self.assertEqual(row.sale_plus_click_earnings, 0.00)
                self.assertEqual(row.total_network_earnings, 0.00)
                self.assertEqual(row.total_clicks, 4)
                self.assertEqual(row.paid_clicks, 0)

    def test_sales_per_click_all_stores_vendor_is_cpo(self):
        """
        Test user earnings and sales are creating correctly when a user belongs to a Commission Group that pays
        all its publishers per click for all stores and has assigned a Publisher network owner with its respective
        owner cut
        """
        group = Group.objects.get(name='Metro Mode')
        cpo_vendor = VendorFactory.create(name="Vendor CPO", is_cpc=False, is_cpo=True)
        CutFactory.create(vendor=cpo_vendor, group=group, cpc_amount=20.00, cpc_currency="EUR", cut=0.6)
        yesterday = (datetime.date.today() - datetime.timedelta(1))
        VendorProductFactory.create(vendor=cpo_vendor, product=self.product_cpo)

        clicks = 4
        for i in range(clicks):
            product_stat = ProductStatFactory.create(ip="1.2.3.4", vendor=cpo_vendor.name, product=self.product_cpo.slug,
                                                     user_id=self.user.id, created=yesterday)
            self.assertTrue(product_stat.is_valid)

        # Run job that generates sales from the summarized clicks from yesterday for user and vendor
        management.call_command('clicks_summary', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(UserEarning.objects.count(), 2)

        # All User earnings might have been created with the right user earning type and amount
        for row in UserEarning.objects.all():
            if row.user_earning_type == "publisher_sale_click_commission_all_stores":
                self.assertEqual(row.amount, 80.00)
                self.assertEqual(row.user, self.user)

        # Run job that aggregates data
        management.call_command('collect_aggregated_data', verbosity=0, interactive=False)

        # Check right amount of AggregatedData instances have been created
        self.assertEqual(AggregatedData.objects.count(), 3)

        for row in AggregatedData.objects.all():
            if row.data_type == "aggregated_from_total":
                if row.user_id == self.user.id:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, 80.00)
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, 0.00)
                    self.assertEqual(row.sale_plus_click_earnings, 80.00)
                    self.assertEqual(row.total_network_earnings, 0.00)
                    self.assertEqual(row.total_clicks, 4)
                    self.assertEqual(row.paid_clicks, 4)
                elif row.user_id == 0:
                    self.assertEqual(row.sale_earnings, 0.00)
                    self.assertEqual(row.click_earnings, 0.00)
                    self.assertEqual(row.referral_earnings, 0.00)
                    self.assertEqual(row.network_sale_earnings, 0.00)
                    self.assertEqual(row.network_click_earnings, 0.00)
                    self.assertEqual(row.sale_plus_click_earnings, 0.00)
                    self.assertEqual(row.total_network_earnings, 0.00)
                    self.assertEqual(row.total_clicks, 0)
                    self.assertEqual(row.paid_clicks, 4)
            elif row.data_type == "aggregated_from_product":
                self.assertEqual(row.user_id, row.user_id)
                self.assertEqual(row.sale_earnings, 0.00)
                self.assertEqual(row.click_earnings, 80.00)
                self.assertEqual(row.referral_earnings, 0.00)
                self.assertEqual(row.network_sale_earnings, 0.00)
                self.assertEqual(row.network_click_earnings, 0.00)
                self.assertEqual(row.sale_plus_click_earnings, 80.00)
                self.assertEqual(row.total_network_earnings, 0.00)
                self.assertEqual(row.total_clicks, 4)
                self.assertEqual(row.paid_clicks, 4)

@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestPayments(TransactionTestCase):

    def test_payments(self):
        owner_user = get_user_model().objects.create_user('owner', 'owner@xvid.se', 'owner')
        owner_user.owner_network_cut = 0.1
        owner_user.save()

        payment_detail = PaymentDetail.objects.create(name='a', company='b', orgnr='c', user=owner_user)

        group = Group.objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        payment_detail = PaymentDetail.objects.create(name='a', company='b', orgnr='c', user=temp_user)

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='50000', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(UserEarning.objects.count(), 3)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)

        #Update a sales transaction
        self.assertEqual(sale.status, Sale.PENDING)
        sale.status = Sale.CONFIRMED
        sale.save()
        self.assertEqual(UserEarning.objects.count(), 3)

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(Payment.objects.count(), 2)

        publisher_payment = Payment.objects.get(user=temp_user)
        self.assertEqual(publisher_payment.amount, 5400)

        owner_payment = Payment.objects.get(user=owner_user)
        self.assertEqual(owner_payment.amount, 600)

        for earning in UserEarning.objects.exclude(user_earning_type='apprl_commission'):
            self.assertEqual(earning.paid, Sale.PAID_READY)

        owner_set = Payment.objects.filter(user=owner_user)

    def test_payments_below_threshold(self):
        group = Group.objects.create(name='mygroup')

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.save()

        payment_detail = PaymentDetail.objects.create(name='a', company='b', orgnr='c', user=temp_user)

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.7, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(UserEarning.objects.count(), 2)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)

        #Update a sales transaction
        self.assertEqual(sale.status, Sale.PENDING)
        sale.status = Sale.CONFIRMED
        sale.save()
        self.assertEqual(UserEarning.objects.count(), 2)

        user_earning = UserEarning.objects.exclude(user_earning_type='apprl_commission')[0]
        self.assertEqual(user_earning.amount, 70)

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(Payment.objects.count(), 0)

    def test_payments_referral_sale(self):
        referral_group = Group.objects.create(name='mygroup')
        referral_user = get_user_model().objects.create_user('referral', 'referral@xvid.se', 'referral')
        referral_user.partner_group = referral_group
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        PaymentDetail.objects.create(name='a', company='b', orgnr='c',
                                                                              user=referral_user)

        group = Group.objects.create(name='mygroup')

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.referral_partner_parent = referral_user
        temp_user.is_partner = True
        temp_user.save()

        payment_detail = PaymentDetail.objects.create(name='a', company='b', orgnr='c',
                                                                              user=temp_user)

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        referral_cut = Cut.objects.create(group=referral_group, vendor=vendor, cut=0.7)
        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)
        store = Store.objects.create(identifier='mystore',
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

        self.assertEqual(Sale.objects.count(), 2)

        for sale in Sale.objects.all():
            # Update a sales transaction
            sale.status = Sale.CONFIRMED
            sale.save()

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(Payment.objects.count(), 2)

        publisher_payment = Payment.objects.get(user=temp_user)
        self.assertEqual(publisher_payment.amount, 600 + 50)

        referral_payment = Payment.objects.get(user=referral_user)
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

        group = Group.objects.create(name='mygroup', owner=owner_user)

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.owner_network = owner_user
        temp_user.save()

        PaymentDetail.objects.create(name='a', company='b', orgnr='c', user=super_master_owner)
        PaymentDetail.objects.create(name='a', company='b', orgnr='c', user=master_owner)
        PaymentDetail.objects.create(name='a', company='b', orgnr='c', user=owner_user)
        PaymentDetail.objects.create(name='a', company='b', orgnr='c', user=temp_user)

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)

        cut = Cut.objects.create(group=group, vendor=vendor, cut=0.6, referral_cut=0.2)

        store_id = 'mystore'
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (temp_user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='5000', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(Sale.objects.count(), 1)

        sale = Sale.objects.get(user_id=temp_user.id, vendor=vendor)
        self.assertEqual(sale.original_commission, 1000)

        self.assertEqual(UserEarning.objects.count(), 5)

        for sale in Sale.objects.all():
            # Update a sales transaction
            sale.status = Sale.CONFIRMED
            sale.save()

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(Payment.objects.count(), 2)

        publisher_payment = Payment.objects.get(user=temp_user)
        self.assertEqual(publisher_payment.amount, 300)

        owner_payment = Payment.objects.get(user=owner_user)
        self.assertEqual(owner_payment.amount, 240)

    def test_payments_user_earnings_history(self):
        group = Group.objects.create(name='mygroup')

        temp_user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        temp_user.partner_group = group
        temp_user.save()

        # Create a sale transactions
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = Vendor.objects.create(name='mystore')
        store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=vendor)
        Cut.objects.create(group=group, vendor=vendor, cut=1, referral_cut=0.2)
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

        self.assertEqual(Sale.objects.count(), 10)

        for sale in Sale.objects.all():
            #Update a sales transaction
            self.assertEqual(sale.status, Sale.PENDING)
            sale.status = Sale.CONFIRMED
            sale.save()

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(Payment.objects.count(), 1)

        # The id of the earnings ready to pay are included in the earning field in the Payment instance
        earnings_ids_list = UserEarning.objects.\
            filter(user=temp_user, status=Sale.CONFIRMED, paid=Sale.PAID_READY).values_list('id', flat=True)

        payment = Payment.objects.get(user=temp_user, paid=False)
        items = json.loads(payment.earnings)

        for earning_id in items:
            self.assertIn(earning_id, earnings_ids_list)

        # The sum of the current earnings ready to pay is the same that the amount of the Payment
        total_query = UserEarning.objects.\
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
        self.vendor = Vendor.objects.create(name='mystore')
        self.vendor_cpc = Vendor.objects.create(name='mystorecpc', is_cpc=True, is_cpo=False)
        self.group = Group.objects.create(name='mygroup')
        self.cut = Cut.objects.create(group=self.group, vendor=self.vendor, cut=0.6,
                                                                referral_cut=0.2)
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        self.store = Store.objects.create(identifier='mystore',
                                                                user=store_user,
                                                                commission_percentage='0.2',
                                                                vendor=self.vendor)

        store_user_cpc = get_user_model().objects.create_user('storecpc', 'storecpc@xvid.se', 'store')
        self.storecpc = Store.objects.create(identifier='mystorecpc',
                                                                user=store_user_cpc,
                                                                vendor=self.vendor_cpc)

        self.user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        self.user.partner_group = self.group
        self.user.name = 'user'
        self.user.owner_network = self.owner_user
        self.user.save()

        category = Category.objects.create(name='Category')
        manufacturer = Brand.objects.create(name='Brand')
        self.product = Product.objects.create(
            product_name='Product',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True
        )
        VendorProduct.objects.create(product=self.product, vendor=self.vendor_cpc)
        ClickCost.objects.create(vendor=self.vendor_cpc, amount=1.00, currency="EUR")

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
        self.assertEqual(Sale.objects.count(), 1)
        # publisher_sale_commission, publisher_network_tribute & apprl_commission: 400,
        self.assertEqual(UserEarning.objects.count(), 3)

        str_date = datetime.date.today().strftime('%Y-%m-%d')
        management.call_command('collect_aggregated_data', date=str_date, verbosity=0, interactive=False)

        # Check total aggregated data generated in total
        self.assertEqual(AggregatedData.objects.count(), 4)

        # Check total aggregated data generated by type
        self.assertEqual(AggregatedData.objects.filter(data_type="aggregated_from_total").
                         count(), 3)
        self.assertEqual(AggregatedData.objects.filter(data_type="aggregated_from_publisher").
                         count(), 1)

        for data in AggregatedData.objects.filter(data_type="aggregated_from_total"):
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
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(UserEarning.objects.count(), 3)

        str_date = datetime.date.today().strftime('%Y-%m-%d')
        management.call_command('collect_aggregated_data', date=str_date, verbosity=0, interactive=False)

        # Check total aggregated data generated in total
        self.assertEqual(AggregatedData.objects.count(), 4)

        # Check total aggregated data generated by type
        self.assertEqual(AggregatedData.objects.filter(data_type="aggregated_from_total").
                         count(), 3)
        self.assertEqual(AggregatedData.objects.filter(data_type="aggregated_from_publisher").
                         count(), 1)

        for data in AggregatedData.objects.filter(data_type="aggregated_from_total"):
            if data.user_id == self.user.id:
                self.assertEqual(data.sale_earnings, decimal.Decimal(540))

            elif data.user_id == self.owner_user.id:
                self.assertEqual(data.network_sale_earnings, decimal.Decimal(60))
                self.assertEqual(data.network_click_earnings, decimal.Decimal(0))
            elif data.user_id == 0:
                self.assertEqual(data.user_name, 'APPRL')
                self.assertEqual(data.sale_earnings, decimal.Decimal(400))

        # Sale is canceled
        sale = Sale.objects.all()[0]
        sale.status = Sale.DECLINED
        sale.save()

        cache_data = cache.get(settings.APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA)
        self.assertNotEqual(cache_data, None)
        management.call_command('update_aggregated_data', verbosity=0, interactive=False)

        cache_data = cache.get(settings.APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA)
        self.assertEqual(cache_data, None)

        for data in AggregatedData.objects.filter(data_type="aggregated_from_total"):
            if data.user_id == self.user.id:
                self.assertEqual(data.sale_earnings, decimal.Decimal(0))

            elif data.user_id == self.owner_user.id:
                self.assertEqual(data.network_sale_earnings, decimal.Decimal(0))
                self.assertEqual(data.network_click_earnings, decimal.Decimal(0))
            elif data.user_id == 0:
                self.assertEqual(data.user_name, 'APPRL')
                self.assertEqual(data.sale_earnings, decimal.Decimal(0))

    def test_product_name_too_long(self):
        category = Category.objects.get(name='Category')
        manufacturer = Brand.objects.get(name='Brand')
        product = Product.objects.create(
            product_name='Adidas Originals adidas Originals White Tubular Runner Sneakers Green Blue White Brown Etc Etc Etc Etc Etc',
            category=category,
            manufacturer=manufacturer,
            gender='M',
            product_image='no real image',
            published=True,
            sku='wk-11111111'
        )
        self.assertGreater(len(product.product_name), 100)
        AggregatedData.objects.create(aggregated_from_name=product.product_name,
                                                                aggregated_from_slug=product.slug)

        self.assertEqual(AggregatedData.objects.count(), 1)
        aggregated_data = AggregatedData.objects.latest("created")
        self.assertEqual(len(aggregated_data.aggregated_from_name), 99)

    def test_fields_none_or_too_long(self):
        long_string = ""
        for i in range(0,205):
            long_string += "a"
        self.assertGreater(len(long_string), 200)

        AggregatedDataFactory.create(aggregated_from_name=None,aggregated_from_slug=None,
                                     aggregated_from_link=None,aggregated_from_image=None)

        AggregatedDataFactory.create(aggregated_from_name=long_string,aggregated_from_slug=long_string,
                                     aggregated_from_link=long_string,aggregated_from_image=long_string)

        self.assertEqual(AggregatedData.objects.count(), 2)
        aggregated_data = AggregatedData.objects.latest("created")
        self.assertEqual(len(aggregated_data.aggregated_from_name), 99)
        self.assertEqual(len(aggregated_data.aggregated_from_slug), 99)
        self.assertEqual(len(aggregated_data.aggregated_from_link), 199)
        self.assertEqual(len(aggregated_data.aggregated_from_image), 199)


class TestAggregatedDataModules(TransactionTestCase):
    def setUp(self):
        self.group = Group.objects.create(name='group_name')
        self.user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        self.user.is_partner = True
        self.user.date_joined = datetime.datetime.strptime("2013-05-07", "%Y-%m-%d")
        self.user.partner_group = self.group
        self.user.save()

    def test_get_aggregated_products_and_publishers(self):
        year = 2015
        month = 1
        order_day = datetime.date(year, month ,15)
        click_day = order_day+relativedelta(days=-1)

        # Generate Earnings and click data with product information
        vendor = VendorFactory.create(name="Vendor Aggregated CPO")
        product = ProductFactory.create(slug="product-number-1", product_name="Product 1")
        VendorProductFactory.create(vendor=vendor, product=product)
        Cut.objects.create(cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, group=self.group,
                                                     vendor=vendor)

        vendor_cpc = VendorFactory.create(name="Vendor Aggregated CPC", is_cpo=False, is_cpc=True)
        product_cpc = ProductFactory.create(slug="product-number-2", product_name="Product 2")
        VendorProductFactory.create(vendor=vendor_cpc, product=product_cpc)
        cut_obj = Cut.objects.create(cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, group=self.group,
                                                     vendor=vendor_cpc)
        click_cost = ClickCost.objects.create(vendor=vendor_cpc, amount=1.00, currency="EUR")

        # Generate clicks for CPO
        for index in range(200):
            ProductStatFactory.create(vendor=vendor.name, is_valid=True, ip= "1.22.3.4", product=product.slug,
                                      created=click_day, user_id=self.user.id)

        # Generate clicks for CPC
        for index in range(100):
            ProductStatFactory.create(vendor=vendor_cpc.name, is_valid=True, ip= "1.22.3.4", product=product_cpc.slug,
                                      created=click_day, user_id=self.user.id)

        self.assertEqual(ProductStat.objects.filter(user_id=self.user.id).count(), 300)

        # Generate earnings CPC,
        management.call_command('clicks_summary', verbosity=0, date="2015-01-14")
        # Management call creates a Sale object based on all clicks previous day (click_day)
        self.assertEqual(Sale.objects.filter(user_id=self.user.id).count(), 1)

        # Generate earnings CPO
        for index in range(1, 11):
            SaleFactory.create(user_id=self.user.id, vendor=vendor, product_id=product.id, created=click_day,
                               sale_date=click_day, pk=index+2)
        self.assertEqual(Sale.objects.filter(user_id=self.user.id).count(), 11)
        self.assertEqual(Sale.objects.filter(user_id=self.user.id, affiliate="cost_per_click").count(), 1)

        # We should have 22 user earnings from 11 sales (10 cpo + 1 cpc), half to user and half to apprl
        self.assertEqual(UserEarning.objects.filter(user=self.user).count(), 11) # to user
        self.assertEqual(UserEarning.objects.filter(user=None).count(), 11)   # to apprl

        # 67 % of 10 x 50 commission sales to user to user based on cut, rest to apprl
        self.assertEqual([33.5] * 10, [u.amount for u in UserEarning.objects.filter(from_product=product, user=self.user)])
        self.assertEqual([16.5] * 10, [u.amount for u in UserEarning.objects.filter(from_product=product, user=None)])

        management.call_command('collect_aggregated_data', verbosity=0, interactive=False, date="2015-01-14")
        
        start_date, end_date = parse_date(year=str(year), month=str(month), first_to_first=True)
        # Check data from get_aggregated_products is correct
        top_products = get_aggregated_products(None, start_date, end_date)
        self.assertEqual(len(top_products), 2)

        cpo_commission = 50 * 10 * decimal.Decimal(cut_obj.cut) # EUR - the 50 comes from Sales factory defaults
        self.assertEqual(top_products[0]['total_earnings'], cpo_commission)
        self.assertEqual(top_products[0]['total_network_earnings'], 0)
        self.assertEqual(top_products[0]['total_clicks'], 200)

        cpc_commission = 100 * 1 * decimal.Decimal(cut_obj.cut) # EUR
        self.assertEqual(top_products[1]['total_earnings'], cpc_commission)
        self.assertEqual(top_products[1]['total_network_earnings'], 0)
        self.assertEqual(top_products[1]['total_clicks'], 100)

        # Check data from get_aggregated_publishers is correct
        top_publishers = get_admin_aggregated_publishers(start_date, end_date)
        publisher_commission = (cpo_commission  + cpc_commission)
        self.assertEqual(len(top_publishers), 1)
        self.assertEqual(top_publishers[0]['user_id'], self.user.id)
        self.assertEqual(top_publishers[0]['total_earnings'], publisher_commission)
        self.assertEqual(top_publishers[0]['total_clicks'], 300)
        self.assertEqual(top_publishers[0]['total_network_earnings'], 0)

        top_publishers = get_admin_aggregated_publishers(start_date, end_date)
        publisher_commission = (cpo_commission  + cpc_commission)
        self.assertEqual(len(top_publishers), 1)
        self.assertEqual(top_publishers[0]['user_id'], self.user.id)
        self.assertEqual(top_publishers[0]['total_earnings'], publisher_commission)
        self.assertEqual(top_publishers[0]['total_clicks'], 300)
        self.assertEqual(top_publishers[0]['total_network_earnings'], 0)

    def test_get_aggregated_products_no_data(self):
        self.assertEqual(Sale.objects.filter(user_id=self.user.id).count(), 0)
        management.call_command('collect_aggregated_data', verbosity=0, interactive=False)
        start_date, end_date = get_current_month_range()

        top_products = get_aggregated_products(None, start_date, end_date)
        self.assertEqual(len(top_products), 0)

    def test_get_aggregated_publisher_no_data(self):
        self.assertEqual(Sale.objects.filter(user_id=self.user.id).count(), 0)
        management.call_command('collect_aggregated_data', verbosity=0, interactive=False)
        start_date, end_date = get_current_month_range()

        top_publishers = get_admin_aggregated_publishers(start_date, end_date)
        self.assertEqual(len(top_publishers), 0)


class TestPaymentHistory(TestCase):

    def test_few_earnings_payments_history(self):
        user = UserFactory.create()
        vendor = VendorFactory.create()
        CutFactory.create(vendor=vendor, group=user.partner_group, cut=0.67)

        for index in range(1, 11):
            SaleFactory.create(user_id=user.id, vendor=vendor)

        self.assertEqual(UserEarning.objects.filter(
            user_earning_type='publisher_sale_commission').count(), 10)

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(Payment.objects.all().count(), 1)

        payment = Payment.objects.all()[0]
        earnings_dict = json.loads(payment.earnings)

        earnings = UserEarning.objects.filter(user_earning_type='publisher_sale_commission')
        for item in earnings:
            self.assertIn(item.id, earnings_dict)

    def test_multiple_earnings_payments_history(self):
        user = UserFactory.create()
        vendor = VendorFactory.create()
        CutFactory.create(vendor=vendor, group=user.partner_group, cut=0.67)

        for index in range(1, 101):
            SaleFactory.create(user_id=user.id, vendor=vendor)

        self.assertEqual(UserEarning.objects.filter(
            user_earning_type='publisher_sale_commission').count(), 100)

        # Ready payments
        management.call_command('dashboard_payment', verbosity=0, interactive=False)

        self.assertEqual(Payment.objects.all().count(), 1)


class TestAdminDashboard(TestCase):

    def test_massive_earnings_admin_dashboard(self):
        user = UserFactory.create()
        vendor = VendorFactory.create()
        product = ProductFactory.create(slug="product")
        VendorProductFactory.create(vendor=vendor, product=product)

        clicks = 1
        for i in range(clicks):
            product_stat = ProductStatFactory.create(ip="1.2.3.4", vendor=vendor.name, product=product.slug)
            self.assertTrue(product_stat.is_valid)


class TestUtils(TransactionTestCase):

    def setUp(self):
        self.group = Group.objects.create(name='group_name')

        self.user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        self.user.is_partner = True
        self.user.date_joined = datetime.datetime.strptime("2014-05-07", "%Y-%m-%d")
        self.user.partner_group = self.group
        self.user.save()

        self.vendor_cpc = VendorFactory.create(name="Vendor CPC", is_cpo=False, is_cpc=True)
        VendorFactory.create(name="Vendor CPO", is_cpo=True, is_cpc=False)

        ClickCost.objects.create(vendor=self.vendor_cpc, amount=1.00, currency="EUR")
        Cut.objects.create(cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, group=self.group,
                                                     vendor=self.vendor_cpc)
        self.short_link = ShortLinkFactory(user=self.user)
        self.long_source_link = 'http://' + 'x'*(SOURCE_LINK_MAX_LEN+10)

    def test_generate_sid_no_data(self):
        product_id = None
        sid = generate_sid(product_id)
        self.assertEqual(sid, "0-0-Default")

    def test_generate_sid_no_product(self):
        product_id = None
        target_user_id = self.user.id
        page = "Ext-Store"
        source_link = self.short_link.link()
        sid = generate_sid(product_id, target_user_id=target_user_id, page=page, source_link=source_link)
        self.assertEqual(sid, "%s-0-%s/%s" % (target_user_id, page, source_link))

    def test_generate_sid(self):
        product_id = 20
        target_user_id = self.user.id
        page = "Ext-Store"
        sid = generate_sid(product_id, target_user_id=target_user_id, page=page)
        self.assertEqual(sid, "%s-%s-%s" % (target_user_id, product_id, page))

    def test_generate_sid_with_source_link(self):
        product_id = 20
        target_user_id = self.user.id
        page = "Ext-Store"
        source_link = self.short_link.link()
        sid = generate_sid(product_id, target_user_id=target_user_id, page=page, source_link=source_link)
        self.assertEqual(sid, "%s-%s-%s/%s" % (target_user_id, product_id, page, source_link))


    def test_generate_sid_with_long_source_link(self):
        product_id = 20
        target_user_id = self.user.id
        page = "Ext-Store"
        sid = generate_sid(product_id, target_user_id=target_user_id, page=page, source_link=self.long_source_link)
        compressed_link = compress_source_link_if_needed(self.long_source_link)
        self.assertEqual(sid, "%s-%s-%s/%s" % (target_user_id, product_id, page, compressed_link))

        redis_key = links_redis_key(self.long_source_link)
        redis_conn = links_redis_connection()
        self.assertIsNotNone(redis_conn.get(redis_key))
        self.assertGreater(redis_conn.ttl(redis_key), 24*60*60*30*2, 'Redis compressed link TTL should be at least two months')

    def test_parse_sid(self):
        sid = "12-21-Ext-Store/http://apprl.com/p/AJSJ"
        user_id, product_id, placement, source_link = parse_sid(sid)
        self.assertEqual(user_id, 12)
        self.assertEqual(product_id, 21)
        self.assertEqual(placement, "Ext-Store")
        self.assertEqual(source_link, "http://apprl.com/p/AJSJ")

    def test_parse_sid_no_data(self):
        sid = ""
        user_id, product_id, placement, source_link = parse_sid(sid)
        self.assertEqual(user_id, 0)
        self.assertEqual(product_id, 0)
        self.assertEqual(placement, "Unknown")
        self.assertEqual(source_link, "")

    def test_parse_sid_no_source_link(self):
        sid = "12-21-Ext-Store"
        user_id, product_id, placement, source_link = parse_sid(sid)
        self.assertEqual(user_id, 12)
        self.assertEqual(product_id, 21)
        self.assertEqual(placement, "Ext-Store")
        self.assertEqual(source_link, "")

    def test_parse_sid_long_source_link(self):
        sid = generate_sid(123, 456, "Ext-Store", source_link=self.long_source_link)
        user_id, product_id, placement, source_link = parse_sid(sid)
        self.assertEqual(product_id, 123)
        self.assertEqual(user_id, 456)
        self.assertEqual(placement, "Ext-Store")
        self.assertEqual(source_link, self.long_source_link)

    def test_map_placement(self):
        self.assertEqual(map_placement('Unknown'), 'Unknown')
        self.assertEqual(map_placement('Ext-Shop'), 'Shop on your site')
        self.assertEqual(map_placement('Ext-Look'), 'Look on your site')
        self.assertEqual(map_placement('Ext-Link'), 'Product link on your site')
        self.assertEqual(map_placement('Ext-Store'), 'Store link on your site')
        self.assertEqual(map_placement('Look'), 'Look on Apprl.com')
        self.assertEqual(map_placement('Shop'), 'Shop on Apprl.com')
        self.assertEqual(map_placement('Feed'), 'Feed on Apprl.com')
        self.assertEqual(map_placement('Profile'), 'Your profile on Apprl.com')
        self.assertEqual(map_placement('Product'), 'Product page')
        self.assertEqual(map_placement('Ext-Banner'), 'Banner on your site')

    def test_get_clicks_from_sale(self):
        yesterday = (datetime.date.today() - datetime.timedelta(1))
        for index in range(100):
            ProductStatFactory.create(vendor="Vendor CPC", is_valid=True, ip="1.2.3.4", created=yesterday,
                                      user_id=self.user.id)
        management.call_command('clicks_summary', verbosity=0, interactive=False)
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.all()[0]
        self.assertEqual(get_clicks_from_sale(sale), 100)

    def test_parse_date_no_date(self):
        """ Test parse_date() function with month and year parameters as None
        """
        year = None
        month = None

        today = datetime.datetime.today()
        first_date = today.replace(day = 1).date()
        last_date = today.replace(day = calendar.monthrange(today.year, today.month)[1]).date()

        start_date, end_date = parse_date(month, year)

        self.assertEqual(start_date, first_date)
        self.assertEqual(end_date, last_date)

    def test_parse_date_custom_date(self):
        """ Test parse_date() function with month and year parameters as not None
        """
        year = "2013"
        month = "5"

        start_date, end_date = parse_date(month, year)

        self.assertEqual(start_date.strftime("%Y-%m-%d"), "2013-05-01")
        self.assertEqual(end_date.strftime("%Y-%m-%d"), "2013-05-31")

    def test_parse_date_first_to_first(self):
        print "Testing extra option for parse date function, first to first"
        today = datetime.date(2015, 04, 01)

        start_date, stop_date = parse_date(today.month, today.year)
        self.assertEquals(start_date, datetime.date(2015, 04, 01))
        self.assertEquals(stop_date, datetime.date(2015, 04, 30))


        start_date, stop_date = parse_date(today.month, today.year, first_to_first=True)
        self.assertEquals(start_date, datetime.date(2015, 04, 01))
        self.assertEquals(stop_date, datetime.date(2015, 05, 01))

        print "Testing first to first option done!"

    def test_enumerate_months(self):
        """ Test months choices, year choices and display text for month passed as input are correct.
        """
        june = 06
        year_list = [row for row in range(self.user.date_joined.year, datetime.date.today().year+1)]

        month_display, month_choices, year_choices = enumerate_months(self.user, june)
        self.assertEqual(month_display, "June")
        self.assertEqual(year_choices, year_list)
        self.assertEqual(len(month_choices), 13) # 12 months  All Year option

    def test_enumerate_months_is_admin(self):
        """ Test months choices, year choices and display text for month passed as input are correct when
        logged as an admin. It should return a list of years since 2011 until the current year.
        """
        june = 06
        year_list = [row for row in range(2011, datetime.date.today().year+1)]

        month_display, month_choices, year_choices = enumerate_months(self.user, june, is_admin=True)
        self.assertEqual(month_display, "June")
        self.assertEqual(year_choices, year_list)
        self.assertEqual(len(month_choices), 13) # 12 months  All Year option

    def test_get_previous_month(self):
        year = "2015"
        month = "05"

        start_date, end_date = parse_date(month, year)
        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

        previous_start_date, previous_end_date = get_previous_period(start_date_query, end_date_query)

        self.assertEqual(previous_start_date, datetime.datetime(2015, 04, 01, 0, 0, 0, 0))
        self.assertEqual(previous_end_date, datetime.datetime(2015, 04, 30, 23, 59, 59, 999999))

        # Initial variables remain the same
        self.assertEqual(start_date_query, datetime.datetime(2015, 05, 01, 0, 0, 0, 0))
        self.assertEqual(end_date_query, datetime.datetime(2015, 05, 31, 23, 59, 59, 999999))

    def test_get_previous_month_if_january(self):
        year = "2016"
        month = "01"

        start_date, end_date = parse_date(month, year)
        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

        previous_start_date, previous_end_date = get_previous_period(start_date_query, end_date_query)

        self.assertEqual(previous_start_date, datetime.datetime(2015, 12, 01, 0, 0, 0, 0))
        self.assertEqual(previous_end_date, datetime.datetime(2015, 12, 31, 23, 59, 59, 999999))

        # Initial variables remain the same
        self.assertEqual(start_date_query, datetime.datetime(2016, 01, 01, 0, 0, 0, 0))
        self.assertEqual(end_date_query, datetime.datetime(2016, 01, 31, 23, 59, 59, 999999))

    def test_get_previous_year(self):
        year = "2015"
        month = "0"

        start_date, end_date = parse_date(month, year)
        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

        previous_start_date, previous_end_date = get_previous_period(start_date_query, end_date_query)

        self.assertEqual(previous_start_date, datetime.datetime(2014, 01, 01, 0, 0, 0, 0))
        self.assertEqual(previous_end_date, datetime.datetime(2014, 12, 31, 23, 59, 59, 999999))

        # Initial variables remain the same
        self.assertEqual(start_date_query, datetime.datetime(2015, 01, 01, 0, 0, 0, 0))
        self.assertEqual(end_date_query, datetime.datetime(2015, 12, 31, 23, 59, 59, 999999))

    def test_relative_change_increase(self):
        previous_value = 203.5
        current_value = 305.25

        percentage_delta = get_relative_change(previous_value, current_value)
        self.assertEqual(percentage_delta, "+50%")

    def test_relative_change_decrease(self):
        previous_value = 305.25
        current_value = 152.625

        percentage_delta = get_relative_change(previous_value, current_value)
        self.assertEqual(percentage_delta, "-50%")

    def test_relative_change_no_change(self):
        previous_value = 203.5
        current_value = 203.5

        percentage_delta = get_relative_change(previous_value, current_value)
        self.assertEqual(percentage_delta, "+0%")

    def test_relative_change_from_zero(self):
        previous_value = 0
        current_value = 203.5

        percentage_delta = get_relative_change(previous_value, current_value)
        self.assertEqual(percentage_delta, None)

    @override_settings(GEOIP_DEBUG=True,GEOIP_RETURN_LOCATION="SE")
    def test_invalid_clicks(self):

        se = Location.objects.create(code='SE')
        vendor_cpc = get_model('apparel', 'Vendor').objects.get(name="Vendor CPC")
        vendor_cpc.locations.add(se)
        vendor_cpo = get_model('apparel', 'Vendor').objects.get(name="Vendor CPO")
        vendor_cpo.locations.add(se)

        for index in range(152):
            ProductStatFactory.create(vendor=vendor_cpc.name, is_valid=False, ip= "1.2.3.4")

        for index in range(27):
            ProductStatFactory.create(vendor=vendor_cpc.name, is_valid=True, ip= "1.2.3.4")

        for index in range(248):
            ProductStatFactory.create(vendor=vendor_cpo.name, is_valid=False, ip= "1.2.3.4")

        for index in range(35):
            ProductStatFactory.create(vendor=vendor_cpo.name, is_valid=True, ip= "1.2.3.4")

        start_date, end_date = get_day_range(datetime.datetime.today())
        invalid_clicks = get_invalid_clicks(start_date, end_date)
        self.assertEqual(invalid_clicks[0], 400)
        self.assertEqual(invalid_clicks[1], 152)
        self.assertEqual(invalid_clicks[2], 248)

    def test_check_user_has_cpc_all_stores_user_is_none(self):
        """
        Test  if method returns False when User is None
        """
        is_cpc_all = check_user_has_cpc_all_stores(None)
        self.assertFalse(is_cpc_all)

    def test_check_user_has_cpc_all_stores_part_group_is_none(self):
        """
        Test if method returns False when User does not belong to a Partner Group
        """
        user = UserFactory.create()
        is_cpc_all = check_user_has_cpc_all_stores(user)
        self.assertFalse(is_cpc_all)

    def test_check_user_has_cpc_all_stores_part_group_is_not_cpc_all_stores(self):
        """
        Test if method returns  false when User is not None, and belongs to a partner group but partner group has
        has_cpc_all_stores set to False
        """
        user = UserFactory.create()
        partner_group = Group.objects.create(name="Group")
        user.partner_group = partner_group
        user.save()

        self.assertFalse(partner_group.has_cpc_all_stores)
        is_cpc_all = check_user_has_cpc_all_stores(user)
        self.assertFalse(is_cpc_all)

    def test_check_user_has_cpc_all_stores_part_group(self):
        """
        Test method return True when user exists, belongs to a partner group and partner group has has_cpc_all_stores
        set to True
        """
        user = UserFactory.create()
        partner_group = Group.objects.create(name="Group", has_cpc_all_stores=True)
        user.partner_group = partner_group
        user.save()

        self.assertTrue(partner_group.has_cpc_all_stores)
        is_cpc_all = check_user_has_cpc_all_stores(user)
        self.assertTrue(is_cpc_all)

class MockRequest(object):
    pass


class TestReferralBonus(TransactionTestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user('test_user', 'testuser@xvid.se', 'Test User')
        self.user.is_partner = True
        self.user.save()

        self.site = AdminSite()
        self.request_obj = MockRequest()

        self.referral_bonus_dict = {'is_promo': True, 'user_id': self.user.pk, 'affiliate': 'referral_promo',
                                'cut': '1.0', 'status': Sale.CONFIRMED, 'exchange_rate': '1.0',
                                'original_sale_id': 'referral_promo_%s' % self.user.pk, 'original_amount': '0.0',
                                'original_commission': '0.0', 'original_currency': 'EUR', 'amount': '0.0',
                                'type': Sale.COST_PER_ORDER, 'commission': '0.0',  'currency': 'EUR',
                                'paid': Sale.PAID_PENDING, 'converted_amount': '0.0', 'converted_commission': '0.0'}

    def test_referral_bonus_from_admin(self):
        """ Test a referral bonus can be created for a user from Django admin and only one time
        """

        sale_admin_form = SaleAdminFormCustom(data=self.referral_bonus_dict)
        self.assertTrue(sale_admin_form.is_valid())

        sale_obj = Sale.objects.create(**self.referral_bonus_dict)

        sa = SaleAdmin(Sale, self.site)

        sa.save_model(request=self.request_obj, obj=sale_obj, form=sale_admin_form, change=False)

        self.assertEqual(Sale.objects.filter(is_promo=True, user_id=self.user.pk).count(), 1)

        referral_bonus = Sale.objects.filter(is_promo=True, user_id=self.user.pk)[0]

        self.assertEqual(referral_bonus.amount, 50)
        self.assertEqual(referral_bonus.currency, "EUR")
        self.assertEqual(referral_bonus.original_amount, 50)
        self.assertEqual(referral_bonus.original_commission, 50)
        self.assertEqual(referral_bonus.original_currency, "EUR")
        self.assertEqual(referral_bonus.converted_amount, 50)
        self.assertEqual(referral_bonus.converted_commission, 50)

        # Test when referral bonus already exists
        sale_admin_form = SaleAdminFormCustom(data=self.referral_bonus_dict)
        self.assertFalse(sale_admin_form.is_valid())

    def test_referral_bonus_from_admin_user_does_not_exist(self):
        """ Test form for create a referral bonus from Django admin is not valid if User with user_id does not exist
        """
        no_user_dict =  self.referral_bonus_dict
        no_user_dict['user_id'] = 9999

        sale_admin_form = SaleAdminFormCustom(data=no_user_dict)
        self.assertFalse(sale_admin_form.is_valid())

    def test_save_not_referral_bonus_from_admin(self):
        """ Test more than one sale with exactly the same parameters and with is_promo=False can be created
        """
        no_referral_bonus =  self.referral_bonus_dict
        no_referral_bonus['is_promo'] = False

        sale_admin_form = SaleAdminFormCustom(data=no_referral_bonus)
        self.assertTrue(sale_admin_form.is_valid())

        sale_obj = Sale.objects.create(**no_referral_bonus)

        sa = SaleAdmin(Sale, self.site)
        sa.save_model(request=self.request_obj, obj=sale_obj, form=sale_admin_form, change=False)
        self.assertEqual(Sale.objects.filter(is_promo=False, user_id=self.user.pk).count(), 1)

        # Test when sale with exactly same values already exists
        sale_admin_form = SaleAdminFormCustom(data=self.referral_bonus_dict)
        self.assertTrue(sale_admin_form.is_valid())
        self.assertEqual(Sale.objects.filter(is_promo=False, user_id=self.user.pk).count(), 1)


class TestStoreCommission(TransactionTestCase):
    fixtures = ['test-fxrates.yaml']

    def setUp(self):
        self.user = get_user_model().objects.create_user('normal_user', 'normal@xvid.se', 'normal')
        self.user.is_partner = True
        self.user.location = "SE"
        self.user.save()
        self.group = GroupFactory.create(name='group_name')

        self.user.partner_group = self.group
        self.user.save()

    def get_store_earnings_cpc_store(self):
        vendor = VendorFactory.create(is_cpc=True)
        CutFactory.create(group=self.group, vendor=vendor)

        store = StoreFactory.create(vendor=vendor)
        standard_from = 0
        _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(self.user.id, vendor)

        ClickCost.objects.create(vendor=vendor, amount=1.5, currency="SEK")
        amount, amount_float, currency, earning_type, type_code = get_store_earnings(self.user, vendor, publisher_cut, normal_cut, standard_from, store)

        self.assertAlmostEqual(amount, decimal.Decimal(1.5) * publisher_cut * normal_cut, 2)
        self.assertAlmostEqual(amount_float, decimal.Decimal(1.5) * publisher_cut * normal_cut, 2)
        self.assertEqual(currency, "SEK")
        self.assertEqual(earning_type, "is_cpc")
        self.assertEqual(type_code, 0)

    def get_store_earnings_cpc_all_stores_rules_exceptions(self):
        rules = [{"sid": self.user.id, "cut": 0.5, "tribute": 0.5}]
        vendor = VendorFactory.create(is_cpc=True)
        cut = CutFactory.create(group=self.group, vendor=vendor, cpc_amount=decimal.Decimal(3.00), cpc_currency="SEK", cut=0.6, rules_exceptions=rules)
        self.group.has_cpc_all_stores = True
        self.group.save()

        store = StoreFactory.create(vendor=vendor)
        standard_from = 0
        _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(self.user.id, vendor)

        ClickCost.objects.create(vendor=vendor, amount=1.5, currency="SEK")
        amount, amount_float, currency, earning_type, type_code = get_store_earnings(self.user, vendor, publisher_cut, normal_cut, standard_from, store)

        self.assertAlmostEqual(decimal.Decimal(amount), cut.locale_cpc_amount * decimal.Decimal(0.5), 2)
        self.assertAlmostEqual(amount_float, cut.locale_cpc_amount * decimal.Decimal(0.5), 2)
        self.assertEqual(currency, cut.locale_cpc_currency)
        self.assertEqual(earning_type, "is_cpc")
        self.assertEqual(type_code, 0)

    def get_store_earnings_cpc_all_stores_rules_exceptions_with_owner(self):
        rules = [{"sid": self.user.id, "cut": 0.5, "tribute": 0.5}]
        vendor = VendorFactory.create(is_cpc=True)
        cut = CutFactory.create(group=self.group, vendor=vendor, cpc_amount=decimal.Decimal(3.00), cpc_currency="EUR",
                          cut=0.6, rules_exceptions=rules)
        self.group.has_cpc_all_stores = True
        self.group.save()

        owner_user = UserFactory.create(owner_network_cut=0.1)
        self.user.owner_network = owner_user
        self.user.save()

        store = StoreFactory.create(vendor=vendor)
        standard_from = 0
        _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(self.user.id, vendor)

        ClickCost.objects.create(vendor=vendor, amount=1.5, currency="SEK")
        amount, amount_float, currency, earning_type, type_code = get_store_earnings(self.user, vendor, publisher_cut, normal_cut, standard_from, store)

        self.assertAlmostEqual(decimal.Decimal(amount), cut.locale_cpc_amount * decimal.Decimal(0.5) * decimal.Decimal(0.5), 2)
        self.assertAlmostEqual(amount_float, cut.locale_cpc_amount * decimal.Decimal(0.5) * decimal.Decimal(0.5), 2)
        self.assertEqual(currency, cut.locale_cpc_currency)
        self.assertEqual(earning_type, "is_cpc")
        self.assertEqual(type_code, 0)

    def get_store_earnings_cpc_all_stores_with_owner(self):
        vendor = VendorFactory.create(is_cpc=True)
        cut = CutFactory.create(group=self.group, vendor=vendor, cpc_amount=decimal.Decimal(3.00), cpc_currency="EUR",
                          cut=0.6)
        self.group.has_cpc_all_stores = True
        self.group.save()

        owner_user = UserFactory.create(owner_network_cut=0.1)
        self.user.owner_network = owner_user
        self.user.save()

        store = StoreFactory.create(vendor=vendor)
        standard_from = 0
        _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(self.user.id, vendor)

        ClickCost.objects.create(vendor=vendor, amount=1.5, currency="SEK")
        amount, amount_float, currency, earning_type, type_code = get_store_earnings(self.user, vendor, publisher_cut, normal_cut, standard_from, store)

        self.assertAlmostEqual(decimal.Decimal(amount), cut.locale_cpc_amount * decimal.Decimal(0.9), 2)
        self.assertAlmostEqual(amount_float, cut.locale_cpc_amount * decimal.Decimal(0.9), 2)
        self.assertEqual(currency, cut.locale_cpc_currency)
        self.assertEqual(earning_type, "is_cpc")
        self.assertEqual(type_code, 0)

    def get_store_earnings_cpc_all_stores(self):
        vendor = VendorFactory.create(is_cpc=True)
        cut = CutFactory.create(group=self.group, vendor=vendor, cpc_amount=decimal.Decimal(3.00), cpc_currency="EUR",
                          cut=0.6)
        self.group.has_cpc_all_stores = True
        self.group.save()

        store = StoreFactory.create(vendor=vendor)
        standard_from = 0
        _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(self.user.id, vendor)

        ClickCost.objects.create(vendor=vendor, amount=1.5, currency="SEK")
        amount, amount_float, currency, earning_type, type_code = get_store_earnings(self.user, vendor, publisher_cut, normal_cut, standard_from, store)

        self.assertAlmostEqual(decimal.Decimal(amount), cut.locale_cpc_amount, 2)
        self.assertAlmostEqual(amount_float, cut.locale_cpc_amount, 2)
        self.assertEqual(currency, cut.locale_cpc_currency)
        self.assertEqual(earning_type, "is_cpc")
        self.assertEqual(type_code, 0)



@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestStatsAdmin(TransactionTestCase):

    def setUp(self):
        flush_stats_cache()
        self.click_dates = set()
        self.order_id = 10000
        self.test_month = 2
        self.test_year = 2016


    def click(self, store, publisher, order_value=0, invalidate_click=False, date_out_of_range=False):
        """
        Simulates a user click on a link created by publisher
        Gives unique order ids and saves the click date so we can run import on that later
        """

        if order_value and not store.vendor.is_cpo:
            raise Exception("Don't pass an order value with a non-cpo vendor")


        month = self.test_month
        if date_out_of_range:
            month += 1
        click_date = datetime.date(self.test_year, month, randint(1, 28))

        with freeze_time(click_date):
            self.click_dates.add(click_date)
            make(ProductStat, vendor=store.vendor.name, user_id=publisher.id if publisher else 0, is_valid=(not invalidate_click))

            page = '%s-Shop' % ((publisher.pk,) if publisher else 0)
            response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'),
                                                                            store.identifier,
                                                                            'http://www.mystore.com/myproduct/',
                                                                            page))
            self.assertEqual(response.status_code, 302)
            if order_value and store.vendor.is_cpo:
                payload = dict(store_id=store.identifier, order_id=str(self.order_id), order_value=order_value, currency='EUR')
                response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(payload)))
                self.assertEqual(response.status_code, 200)
                self.order_id += 1
                return self.order_id - 1


    def get_click_dates(self):
        return [d.strftime('%Y-%m-%d') for d in self.click_dates]


    def collect_clicks(self):
        # we run the import on the first of the month after our test month
        import_date = datetime.date(self.test_year, self.test_month+1, 1)
        with freeze_time(import_date):
            for day in self.get_click_dates():
                management.call_command('clicks_summary', verbosity=0, date=day)
            management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)


    def create_users(self, ppc_as=False, create_referral_partner=True):
        publisher = make(get_user_model(),
                                is_partner=True,
                                partner_group__has_cpc_all_stores=ppc_as
                                )
        if create_referral_partner:
            # Referral user - should get kickbacks on whatever publisher is making
            with freeze_time(datetime.date(self.test_year, self.test_month, 1)):
                publisher.referral_partner_parent = make(get_user_model(),
                                                                is_partner=True,
                                                                referral_partner=True,
                                                                partner_group=publisher.partner_group)
                publisher.save()
        return publisher


    def test_top_stats_ppc_as_publisher(self):

        # Create users

        ppc_as_publisher = self.create_users(ppc_as=True, create_referral_partner=True)


        # Create stores / vendors. We only create AAN vendors because it allows us to control commission_percentage

        cpo_store = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v', commission_percentage='0.2')
        cpc_store = make(Store, vendor__is_cpc=True, vendor__is_cpo=False, vendor__name='cpc_v')
        make(ClickCost, vendor=cpc_store.vendor, amount=5)
        make(Cut, vendor=cpo_store.vendor, group=ppc_as_publisher.partner_group, cut=0, cpc_amount=3, referral_cut=0.1)
        make(Cut, vendor=cpc_store.vendor, group=ppc_as_publisher.partner_group, cut=0, cpc_amount=3, referral_cut=0.1)


        # Create clicks, both valid and invalid

        self.click(cpo_store, ppc_as_publisher, order_value=500)   # with 20% commission = 100. 3 to ppc_as publisher
        self.click(cpo_store, None, order_value=600)   # with 20% commission = 120 - all goes to Apprl
        self.click(cpo_store, ppc_as_publisher, invalidate_click=True)   # click shouldn't count
        self.click(cpo_store, ppc_as_publisher)    # no cpo conversion, but ppc_as publisher still gets 3

        self.click(cpc_store, ppc_as_publisher)    # 3 to ppc_as publisher. vendor pays 5
        self.click(cpc_store, ppc_as_publisher, invalidate_click=True)   # shouldn't count
        self.click(cpc_store, ppc_as_publisher, date_out_of_range=True)   # this one shouldn't count in stats since it's out of range


        # Collect clicks, generate sales & user earnings.

        self.collect_clicks()


        # Test it!

        tr = mrange(self.test_year, self.test_month)

        self.assertEqual(stats_admin.earnings_total(tr), 225)    # 100 + 120 commission from cpo sales + 5 cpc click cost
        self.assertEqual(stats_admin.earnings_publisher(tr), 9)  # 3 valid ppc_as clicks x 3 = 9
        self.assertEqual(stats_admin.earnings_apprl(tr), 225 - 9)  # defined as total - publisher

        self.assertEqual(stats_admin.referral_earnings_total(tr), 0)         # by definition
        self.assertEqual(stats_admin.referral_earnings_publisher(tr), D('50.9'))  # 50 (default signup bonus) + 10% (defined in Cuts) of 9 (publisher earnings)
        self.assertEqual(stats_admin.referral_earnings_apprl(tr), D('-50.9'))     # -publisher earnings by definition

        self.assertEqual(stats_admin.ppo_commission_total(tr), 220)
        self.assertEqual(stats_admin.ppo_commission_publisher(tr), 0)    # by definition
        self.assertEqual(stats_admin.ppo_commission_apprl(tr), 0)        # by definition

        self.assertEqual(stats_admin.ppc_commission_total(tr), 5)        # 1 click to ppc store
        self.assertEqual(stats_admin.ppc_commission_publisher(tr), 0)    # by defintion
        self.assertEqual(stats_admin.ppc_commission_apprl(tr), 0)        # by definition

        self.assertEqual(stats_admin.ppc_clicks_total(tr), 2)            # by definition
        self.assertEqual(stats_admin.ppc_clicks_publisher(tr), 2)        # incl. invalid
        self.assertEqual(stats_admin.ppc_clicks_apprl(tr), 0)

        self.assertEqual(stats_admin.ppo_clicks_total(tr), 4)            # by definition
        self.assertEqual(stats_admin.ppo_clicks_publisher(tr), 3)        # incl. invalid
        self.assertEqual(stats_admin.ppo_clicks_apprl(tr), 1)

        self.assertEqual(stats_admin.ppo_sales_total(tr), 2)
        self.assertEqual(stats_admin.ppo_sales_publisher(tr), 1)
        self.assertEqual(stats_admin.ppo_sales_apprl(tr), 1)

        self.assertEqual(stats_admin.commission_cr_total(tr), D(2) / D(4))         # 2/4 (ppo sales tot / ppo clicks tot)
        self.assertEqual(stats_admin.commission_cr_publisher(tr), D(1) / D(3))     # 1/3 (ppo sales pub / ppo clicks pub)
        self.assertEqual(stats_admin.commission_cr_apprl(tr), D(1) / D(1))         # 1/3 (ppo sales apprl / ppo clicks apprl)

        self.assertEqual(stats_admin.average_epc_total(tr), D(225) / 6)         # 5+100+120 (ppx commission) / 2+4 (ppx clicks incl. invalid)
        self.assertEqual(stats_admin.average_epc_ppc(tr), 2.5)               # 5/2 (ppc commission / ppc clicks)
        self.assertEqual(stats_admin.average_epc_ppo(tr), D(220) / 4)           # 100+120/3 (ppo commission / ppo clicks)

        self.assertEqual(stats_admin.valid_clicks_total(tr), 4)
        self.assertEqual(stats_admin.valid_clicks_ppc(tr), 1)
        self.assertEqual(stats_admin.valid_clicks_ppo(tr), 3)

        self.assertEqual(stats_admin.invalid_clicks_total(tr), 2)
        self.assertEqual(stats_admin.invalid_clicks_ppc(tr), 1)
        self.assertEqual(stats_admin.invalid_clicks_ppo(tr), 1)

        self.assertEqual(stats_admin.ppc_all_stores_publishers_income(tr), 100)  # ppo income generated by ppc_as publishers
        self.assertEqual(stats_admin.ppc_all_stores_publishers_cost(tr), 6)      # earnings paid out to ppc_as publishers for clicks to ppo publishers
        self.assertEqual(stats_admin.ppc_all_stores_publishers_result(tr), 94)    # by definition


    def test_top_stats_normal_publisher(self):

        # Create users

        publisher = self.create_users(ppc_as=False, create_referral_partner=True)


        # Create stores / vendors. We only create AAN vendors because it allows us to control commission_percentage

        cpo_store = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v', commission_percentage='0.2')
        cpc_store = make(Store, vendor__is_cpc=True, vendor__is_cpo=False, vendor__name='cpc_v')
        make(ClickCost, vendor=cpc_store.vendor, amount=5)
        make(Cut, vendor=cpo_store.vendor, group=publisher.partner_group, cut=0.3, referral_cut=0.1)
        make(Cut, vendor=cpc_store.vendor, group=publisher.partner_group, cut=0.1, referral_cut=0.1)


        # Create clicks, both valid and invalid

        self.click(cpo_store, publisher, order_value=1000)   # with 20% commission = 200
        self.click(cpo_store, None, order_value=300)   # with 20% commission = 60 - all goes to Apprl
        self.click(cpo_store, publisher, invalidate_click=True, order_value=200)   # click shouldn't count, but sale goes through so we still get 20% commission - 40
        self.click(cpo_store, publisher)    # no cpo conversion

        self.click(cpc_store, publisher)    # vendor pays 5 - publisher gets 0.5 (10% cut)
        self.click(cpc_store, None)         # vendor pays 5 - apprl gets all of it
        self.click(cpc_store, publisher, invalidate_click=True)   # click shouldn't count it is invalid
        self.click(cpc_store, publisher=publisher, date_out_of_range=True)   # this one shouldn't count in stats since it's out of range


        # Collect clicks, generate sales & user earnings.

        self.collect_clicks()


        # Test it!

        tr = mrange(self.test_year, self.test_month)

        self.assertEqual(stats_admin.earnings_total(tr), 310)    # 200 + 60 + 40 commission from cpo sales + 5 + 5 cpc
        self.assertEqual(stats_admin.earnings_publisher(tr), 72 + 0.5)  # (200 + 40)*0.3 + 5*0.1
        self.assertEqual(stats_admin.earnings_apprl(tr), 310 - 72.5)  # defined as total - publisher

        # Referral cuts are wrongly calculated on sale commission, should be based on publisher
        # earnings. https://www.pivotaltracker.com/n/projects/243709
        self.assertEqual(stats_admin.referral_earnings_total(tr), 0)         # by definition
        self.assertEqual(stats_admin.referral_earnings_publisher(tr), 74.5)  # 50 (default signup bonus) + 10% (defined in Cuts) of 200+40+5.
        self.assertEqual(stats_admin.referral_earnings_apprl(tr), -74.5)     # -publisher earnings by definition

        self.assertEqual(stats_admin.ppo_commission_total(tr), 300)       # 200 + 60 + 40
        self.assertEqual(stats_admin.ppo_commission_publisher(tr), 0)    # by definition
        self.assertEqual(stats_admin.ppo_commission_apprl(tr), 0)        # by definition

        self.assertEqual(stats_admin.ppc_commission_total(tr), 10)        # 1 click to ppc store
        self.assertEqual(stats_admin.ppc_commission_publisher(tr), 0)    # by defintion
        self.assertEqual(stats_admin.ppc_commission_apprl(tr), 0)        # by definition

        self.assertEqual(stats_admin.ppc_clicks_total(tr), 3)            # by definition
        self.assertEqual(stats_admin.ppc_clicks_publisher(tr), 2)        # incl. invalid
        self.assertEqual(stats_admin.ppc_clicks_apprl(tr), 1)

        self.assertEqual(stats_admin.ppo_clicks_total(tr), 4)            # by definition
        self.assertEqual(stats_admin.ppo_clicks_publisher(tr), 3)        # incl. invalid
        self.assertEqual(stats_admin.ppo_clicks_apprl(tr), 1)

        self.assertEqual(stats_admin.ppo_sales_total(tr), 3)
        self.assertEqual(stats_admin.ppo_sales_publisher(tr), 2)
        self.assertEqual(stats_admin.ppo_sales_apprl(tr), 1)

        self.assertEqual(stats_admin.commission_cr_total(tr), D(3) / D(4))         # 3/4 (ppo sales tot / ppo clicks tot)
        self.assertEqual(stats_admin.commission_cr_publisher(tr), D(2) / D(3))     # 2/3 (ppo sales pub / ppo clicks pub)
        self.assertEqual(stats_admin.commission_cr_apprl(tr), D(1) / D(1))         # 1/3 (ppo sales apprl / ppo clicks apprl)

        self.assertEqual(stats_admin.average_epc_total(tr), D(310) / 7)         # (ppx commission) / (ppx clicks incl. invalid)
        self.assertEqual(stats_admin.average_epc_ppc(tr), D(10) / 3)               # (ppc commission / ppc clicks)
        self.assertEqual(stats_admin.average_epc_ppo(tr), D(300) / 4)           # (ppo commission / ppo clicks)

        self.assertEqual(stats_admin.valid_clicks_total(tr), 5)
        self.assertEqual(stats_admin.valid_clicks_ppc(tr), 2)
        self.assertEqual(stats_admin.valid_clicks_ppo(tr), 3)

        self.assertEqual(stats_admin.invalid_clicks_total(tr), 2)
        self.assertEqual(stats_admin.invalid_clicks_ppc(tr), 1)
        self.assertEqual(stats_admin.invalid_clicks_ppo(tr), 1)

        self.assertEqual(stats_admin.ppc_all_stores_publishers_income(tr), 0)
        self.assertEqual(stats_admin.ppc_all_stores_publishers_cost(tr), 0)
        self.assertEqual(stats_admin.ppc_all_stores_publishers_result(tr), 0)


    def test_all_stores_stats(self):

        # Create users

        ppc_as_publisher = self.create_users(ppc_as=True, create_referral_partner=True)


        # Create stores / vendors. We only create AAN vendors because it allows us to control commission_percentage

        cpo_store = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v', commission_percentage='0.2')
        cpo_store_2 = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v_2', commission_percentage='0.2')
        cpc_store = make(Store, vendor__is_cpc=True, vendor__is_cpo=False, vendor__name='cpc_v')
        make(ClickCost, vendor=cpc_store.vendor, amount=5)
        make(Cut, vendor=cpo_store.vendor, group=ppc_as_publisher.partner_group, cut=0, cpc_amount=3, referral_cut=0.1)
        make(Cut, vendor=cpo_store_2.vendor, group=ppc_as_publisher.partner_group, cut=0, cpc_amount=5, referral_cut=0.1)
        make(Cut, vendor=cpc_store.vendor, group=ppc_as_publisher.partner_group, cut=0, cpc_amount=3, referral_cut=0.1)


        # Create clicks, both valid and invalid

        self.click(cpo_store, ppc_as_publisher, order_value=500)   # with 20% commission = 100. 3 to ppc_as publisher
        self.click(cpo_store, None, order_value=600)   # with 20% commission = 120 - all goes to Apprl
        self.click(cpo_store, ppc_as_publisher, invalidate_click=True)   # click shouldn't count
        self.click(cpo_store, ppc_as_publisher)    # no cpo conversion, but ppc_as publisher still gets 3

        self.click(cpo_store_2, ppc_as_publisher, order_value=1000)   # with 20% commission = 200. 5 to ppc_as publisher

        self.click(cpc_store, ppc_as_publisher)    # 3 to ppc_as publisher. vendor pays 5
        self.click(cpc_store, ppc_as_publisher, invalidate_click=True)   # shouldn't count
        self.click(cpc_store, ppc_as_publisher, date_out_of_range=True)   # this one shouldn't count in stats since it's out of range


        # Collect clicks, generate sales & user earnings.

        self.collect_clicks()


        # Test it!

        tr = mrange(self.test_year, self.test_month)

        vendor_stats = stats_admin.ppc_all_stores_publishers_by_vendor(tr)
        self.assertEqual(set(vendor_stats.keys()), set(['cpo_v', 'cpo_v_2']))       # we only care about the cpo vendors
        self.assertEqual(vendor_stats['cpo_v']['income'], 100)          # the vendor pays us 100 commission
        self.assertEqual(vendor_stats['cpo_v']['cost'], 3+3)            # two payouts with 3
        self.assertEqual(vendor_stats['cpo_v']['result'], 94)           # income - cost

        self.assertEqual(stats_admin.ppc_all_stores_publishers_income(tr), 100+200)
        self.assertEqual(stats_admin.ppc_all_stores_publishers_cost(tr), 3+3+5)
        self.assertEqual(stats_admin.ppc_all_stores_publishers_result(tr), 300-11)


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestStatsCache(TransactionTestCase):


    def setUp(self):
        stats_redis.flushall()


    def test_stats_caching(self):
        @stats_cache
        def foo(time_range):
            return testval

        testval = 1
        self.assertEqual(foo(mrange(2016, 8)), 1)
        
        self.assertEqual(
            set(stats_redis.keys('*')),
            set([cache_key(mrange(2016, 8), 'foo'), 'stats_ranges_right', 'stats_ranges_left'])
        )

        testval = 2
        self.assertEqual(foo(mrange(2016, 8)), 1)   # old value should be returned

        flush_stats_cache()
        testval = 3
        self.assertEqual(foo(mrange(2016, 8)), 3)   # cache flushed so function returns new value

        flush_stats_cache_by_year(2016)
        testval = 4
        self.assertEqual(foo(mrange(2016, 8)), 4)   # cache flushed so function returns new value

        flush_stats_cache_by_year(2017)
        testval = 5
        self.assertEqual(foo(mrange(2016, 8)), 4)   # cache flushed outside range so function retains previous value

        flush_stats_cache_by_month(2016, 8)
        testval = 6
        self.assertEqual(foo(mrange(2016, 8)), 6)   # cache flushed - new value

        flush_stats_cache_by_month(2016, 9)
        testval = 7
        self.assertEqual(foo(mrange(2016, 8)), 6)   # cache flushed outside range - function retains previous value


    def test_different_functions_caching(self):
        @stats_cache
        def foo(time_range):
            return testval

        @stats_cache
        def bar(time_range):
            return testval

        testval = 1
        self.assertEqual(foo(mrange(2016, 8)), 1)
        testval = 2
        self.assertEqual(bar(mrange(2016, 8)), 2)

        testval = 3
        self.assertEqual(foo(mrange(2016, 8)), 1)   # should retain cached value
        self.assertEqual(bar(mrange(2016, 8)), 2)   # should retain cached value

        self.assertEqual(
            set(stats_redis.keys('*')),
            set([
                cache_key(mrange(2016, 8), 'foo'),
                cache_key(mrange(2016, 8), 'bar'),
                'stats_ranges_right',
                'stats_ranges_left'
            ])
        )


    def test_different_arguments_caching(self):
        @stats_cache
        def foo(time_range, param):
            return testval

        testval = 1
        self.assertEqual(foo(mrange(2016, 8), 666), 1)
        testval = 2
        self.assertEqual(foo(mrange(2016, 8), 777), 2)

        testval = 3
        self.assertEqual(foo(mrange(2016, 8), 666), 1)   # should retain cached value
        self.assertEqual(foo(mrange(2016, 8), 777), 2)   # should retain cached value

        self.assertEqual(
            set(stats_redis.keys('*')),
            set([
                cache_key(mrange(2016, 8), 'foo', (666)),
                cache_key(mrange(2016, 8), 'foo', (777)),
                'stats_ranges_right',
                'stats_ranges_left'
            ])
        )


    def test_sales_changes_should_flush_cache(self):
        publisher = make(get_user_model(), is_partner=True, partner_group__has_cpc_all_stores=False)
        cpo_store = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v')
        make(Cut, vendor=cpo_store.vendor, group=publisher.partner_group)

        sale = make(Sale, sale_date=datetime.date(2016, 8, 1), user_id=publisher.pk, vendor=cpo_store.vendor, converted_commission=100, status=Sale.PENDING)
        self.assertEqual(stats_admin.ppo_commission_total(mrange(2016, 8)), 100)

        sale.converted_commission = 200
        sale.save()
        self.assertEqual(stats_admin.ppo_commission_total(mrange(2016, 8)), 200)

