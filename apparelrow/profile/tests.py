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

from localeurl.utils import locale_url


def reverse_locale(*args, **kwargs):
    return locale_url(reverse(*args, **kwargs), 'en')


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestProfile(TransactionTestCase):

    def test_signup(self):
        response = self.client.post(reverse_locale('auth_register_email'), {'first_name': 'test',
                                                                            'last_name': 'svensson',
                                                                            'username': 'test',
                                                                            'email': 'test@xvid.se',
                                                                            'password1': 'test',
                                                                            'password2': 'test',
                                                                            'gender': 'M'})

        user = get_user_model().objects.get(email='test@xvid.se')
        self.assertFalse(user.is_active)

        self.assertEqual(len(mail.outbox), 2)
        welcome_mail_body = mail.outbox[1].body
        activation_url = re.search(r'http:\/\/testserver(.+)', welcome_mail_body).group(1)
        response = self.client.get(activation_url)

        user = get_user_model().objects.get(email='test@xvid.se')
        self.assertTrue(user.is_active)
