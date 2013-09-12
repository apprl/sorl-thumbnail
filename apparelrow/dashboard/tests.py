import re
import urllib
import decimal

from django.conf import settings
from django.core import mail
from django.core import signing
from django.core.urlresolvers import reverse
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from django.core import management


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

        response = self.client.get(referral_url)
        self.assertRedirects(response, reverse('index-publisher'))
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

        response = self.client.get(referral_url)
        self.assertRedirects(response, reverse('index-publisher'))
        self.assertNotIn(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME, response.client.cookies.keys())

    def test_signup_from_referral_link(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        # Visit referral URL
        response = self.client.get(referral_user.get_referral_url())
        self.assertRedirects(response, reverse('index-publisher'))

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
        self.assertEqual(response.client.cookies.get(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME).value, '')

        # Admin goes in and mark the user as partner which in turn sets the parent date
        registered_user.is_partner = True
        registered_user.save()
        self.assertIsNotNone(registered_user.referral_partner_parent_date)

    def test_signup_from_invalid_referral_link(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        # Visit referral URL
        response = self.client.get(referral_user.get_referral_url())
        self.assertRedirects(response, reverse('index-publisher'))

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
        self.assertEqual(response.client.cookies.get(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME).value, '')

    def test_visit_two_referral_links(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        # Visit referral URL, register by email and activate account
        response = self.client.get(referral_user.get_referral_url())
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
        self.assertEqual(response.client.cookies.get(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME).value, '')

        # Must delete cookie manually because the test suite does not remove
        # invalid cookies like a browser
        del response.client.cookies[settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME]

        # Admin goes in and mark the user as partner which in turn sets the parent date
        registered_user.is_partner = True
        registered_user.save()

        another_user = get_user_model().objects.create_user('another_user', 'another@xvid.se', 'another')
        another_user.referral_partner = True
        another_user.is_partner = True
        another_user.save()

        response = self.client.get(another_user.get_referral_url())
        response = self.client.get('/')

        registered_user = get_user_model().objects.get(email='test@xvid.se')
        self.assertEqual(registered_user.referral_partner_parent, referral_user)
        self.assertIsNotNone(registered_user.referral_partner_parent_date)
        self.assertEqual(response.client.cookies.get(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME).value, '')

    def test_referral_sale(self):
        referral_user = get_user_model().objects.create_user('referral_user', 'referral@xvid.se', 'referral')
        referral_user.referral_partner = True
        referral_user.is_partner = True
        referral_user.save()

        # Visit referral URL, register by email and activate account
        response = self.client.get(referral_user.get_referral_url())
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
        normal_sale = get_model('dashboard', 'Sale').objects.get(is_referral_sale=False)
        self.assertFalse(normal_sale.is_referral_sale)
        self.assertIsNone(normal_sale.referral_user)
        self.assertEqual(normal_sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

        referral_user_sale = get_model('dashboard', 'Sale').objects.get(is_referral_sale=True)
        self.assertTrue(referral_user_sale.is_referral_sale)
        self.assertEqual(referral_user_sale.referral_user, registered_user)
        self.assertEqual(referral_user_sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT))

        # Repeat the import of the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 2)

        # Verify it
        normal_sale = get_model('dashboard', 'Sale').objects.get(is_referral_sale=False)
        self.assertFalse(normal_sale.is_referral_sale)
        self.assertIsNone(normal_sale.referral_user)
        self.assertEqual(normal_sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

        referral_user_sale = get_model('dashboard', 'Sale').objects.get(is_referral_sale=True)
        self.assertTrue(referral_user_sale.is_referral_sale)
        self.assertEqual(referral_user_sale.referral_user, registered_user)
        self.assertEqual(referral_user_sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT))

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

    def test_default_cut(self):
        # Create a partner user
        user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        user.is_partner = True
        user.save()

        # Create a sale transactions
        store_id = 'mystore'
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name=store_id)
        store = get_model('advertiser', 'Store').objects.create(identifier=store_id, user=store_user, commission_percentage='0.2', vendor=vendor)
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

        # Import the sale transaction
        management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)

        # Verify sale transaction
        self.assertEqual(get_model('dashboard', 'Sale').objects.count(), 1)
        sale = get_model('dashboard', 'Sale').objects.get()
        self.assertIsNotNone(sale)
        self.assertEqual(sale.commission, decimal.Decimal(100) * decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT))

    def test_non_default_cut(self):
        # Create a partner user
        user = get_user_model().objects.create_user('user', 'user@xvid.se', 'user')
        user.is_partner = True
        user.save()

        # Create a sale transactions
        store_id = 'mystore'
        store_user = get_user_model().objects.create_user('store', 'store@xvid.se', 'store')
        vendor = get_model('apparel', 'Vendor').objects.create(name=store_id)
        store = get_model('advertiser', 'Store').objects.create(identifier=store_id, user=store_user, commission_percentage='0.2', vendor=vendor)
        url = 'http://www.mystore.com/myproduct/'
        custom = '%s-Shop' % (user.pk,)
        response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'), store_id, url, custom))
        self.assertEqual(response.status_code, 302)
        response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(dict(store_id='mystore', order_id='1234', order_value='500', currency='EUR'))))
        self.assertEqual(response.status_code, 200)

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
