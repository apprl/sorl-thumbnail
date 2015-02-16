import re
import urllib
import decimal
import json

from django.conf import settings
from django.core import mail
from django.core import signing
from django.core.urlresolvers import reverse as _reverse
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.core import management

from localeurl.utils import locale_url
from apparelrow.apparel.models import Vendor
from apparelrow.dashboard.models import Group, StoreCommission, Cut, Sale

from apparelrow.dashboard.utils import get_cuts_for_user_and_vendor
from apparelrow.dashboard.admin import PaymentAdmin
from jsonfield import JSONField



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

    def test_referral_link(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        referral_url = referral_user.get_referral_url()
        self.assertRegexpMatches(referral_url, r'\/i\/\w{4,16}')

        response = self.client.get(referral_url, follow=True)
        self.assertRedirects(response, reverse('publisher-contact'))
        self.assertIn(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME, response.client.cookies.keys())

        # decode cookie manually and verify content
        cookie_key = settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME
        signed_cookie_value = response.client.cookies.get(cookie_key).value
        value = signing.get_cookie_signer(salt=cookie_key).unsign(signed_cookie_value, max_age=None)
        self.assertEqual(str(value), str(referral_user.pk))

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

    def test_signup_from_referral_link(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

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

        # Click on activation email
        welcome_mail_body = mail.outbox[2].body
        activation_url = re.search(r'http:\/\/testserver(.+)', welcome_mail_body).group(1)
        response = self.client.get(activation_url)

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

        welcome_mail_body = mail.outbox[2].body
        activation_url = re.search(r'http:\/\/testserver(.+)', welcome_mail_body).group(1)
        response = self.client.get(activation_url)

        registered_user = get_user_model().objects.get(email='test@xvid.se')
        self.assertIsNone(registered_user.referral_partner_parent)
        self.assertIsNone(registered_user.referral_partner_parent_date)

        # Invalid referral link should not result in a promo sale of 20 EUR
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 0)

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

    def test_referral_sale(self):
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

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 2)

        # Verify it
        referral_user_sale = get_model('dashboard', 'Sale').objects.get(is_referral_sale=True, is_promo=False,)
        self.assertTrue(referral_user_sale.is_referral_sale)
        self.assertEqual(referral_user_sale.referral_user, referral_user)
        self.assertEqual(referral_user_sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

        # Repeat the import of the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 2)

        # Verify it
        referral_user_sale = get_model('dashboard', 'Sale').objects.get(is_promo=False, is_referral_sale=True)
        self.assertTrue(referral_user_sale.is_referral_sale)
        self.assertEqual(referral_user_sale.referral_user, referral_user)
        self.assertEqual(referral_user_sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

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

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        # Verify sale transaction
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
        self.assertIsNotNone(sale)
        self.assertEqual(sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

    def test_non_default_cut(self):
        user = self._create_partner_user()
        vendor, transaction = self._create_transaction(user, order_value='500')

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
        self.assertIsNotNone(sale)
        self.assertEqual(sale.commission, decimal.Decimal(100) * decimal.Decimal('0.9'))

    def test_update_cut(self):
        user = self._create_partner_user()
        vendor, transaction = self._create_transaction(user, order_value='500')

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
        group = get_model('dashboard', 'Group').objects.create(name='mygroup')
        cut = get_model('dashboard', 'Cut').objects.create(group=group, vendor=vendor, cut=settings.APPAREL_DASHBOARD_CUT_DEFAULT, referral_cut=0.2)

        user.partner_group = group
        user.save()

        # 1. Import the sale transaction and verify it
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
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
    '''
        Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
        owner doesn't belong to a Publisher Network
    '''
    def test_user_earnings_publisher_network(self):
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

    '''
        Tests UserEarnings that are generated when the user doesn't belong to a Publisher Network
    '''
    def test_user_earnings_no_publisher_network(self):
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

    '''
        Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
        owner belongs to a Publisher Network recursively
    '''
    def test_user_earnings_recursive_publisher_network(self):

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

    '''
        Tests UserEarnings when user doesn't belong to a Commission Group
    '''
    def test_user_earnings_no_commission_group(self):
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

    '''
        Tests UserEarnings when a referral Sale is made
    '''
    def test_user_earnings_referral_sale(self):
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

    '''
        Tests UserEarnings when a direct sales is generated on APPRL.com
    '''
    def test_user_earning_apprl_direct_sale(self):
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

        sale = get_model('dashboard', 'Sale').objects.get(user_id=temp_user.id, vendor=vendor)

        #Update a sales transaction
        self.assertEqual(sale.status, get_model('dashboard', 'Sale').PENDING)
        sale.status = get_model('dashboard', 'Sale').CONFIRMED
        sale.save()

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

    '''
        Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
        owner doesn't belong to a Publisher Network with cuts exceptions
    '''

    def test_commissions_publisher_network_with_exceptions(self):
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


    '''
        Tests UserEarnings that are generated when the user belongs to a Publisher Network and the Publisher Network
        owner belongs to a Publisher Network recursively with cuts exceptions
    '''
    def test_commissions_recursive_publisher_network_with_exceptions(self):
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

