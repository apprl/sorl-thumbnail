from django.contrib.sites.models import Site
import re

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model

from django.test import Client

from localeurl.utils import locale_url
from apparelrow.apparel.models import Look
from apparelrow.profile.forms import RegisterForm
from apparelrow.profile.notifications import retrieve_full_url, retrieve_static_url


def reverse_locale(*args, **kwargs):
    return locale_url(reverse(*args, **kwargs), 'en')


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestProfile(TransactionTestCase):
    def test_signup(self):
        c = Client()
        response = c.post(reverse('auth_register_email'), {'first_name': 'test',
                                                                    'last_name': 'svensson',
                                                                    'username': 'test',
                                                                    'email': 'test@xvid.se',
                                                                    'password1': 'test',
                                                                    'password2': 'test',
                                                                    'gender': 'M'})
        user = get_user_model().objects.get(username='test')
        self.assertFalse(user.is_active)

        mailbox = mail.outbox
        self.assertEqual(len(mailbox), 2)
        welcome_mail_body = mailbox[1].body
        print "Sent mail check passed"
        activation_url = re.search(r'http:\/\/testserver(.+)', welcome_mail_body).group(1)
        # Sometimes an additional \r gets included in the url forcing a 404
        activation_url = activation_url.replace("\r","")
        response = self.client.get(activation_url)
        self.assertEqual(response.status_code,302)
        user = get_user_model().objects.get(email='test@xvid.se')
        self.assertTrue(user.is_active)
        print "Verified user is active"

    def test_signup_email_already_registered(self):
        get_user_model().objects.create(name="Blogger Test", username="usertest", slug="user_test",
                                        email="user@test.com")

        form_data = {'first_name': 'test',
                     'last_name': 'svensson',
                     'username': 'test',
                     'email': 'user@test.com',
                     'password1': 'test',
                     'password2': 'test',
                     'gender': 'M'}

        form = RegisterForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEquals(form.errors['email'], [u"A user with that e-mail already exists."])

class TestUtilities(TestCase):
    temp_static_url = "http://s-staging.apprl.com/"

    @override_settings(STATIC_URL="http://s-staging.apprl.com/")
    def test_retrieve_full_url(self):
        from django.conf import settings
        print "Test generating full url"
        url = retrieve_full_url("someimage.png")
        self.assertEqual(settings.STATIC_URL,self.temp_static_url)
        self.assertEqual("http://s-staging.apprl.com/someimage.png",url)
        print "Test passed"

    @override_settings(STATIC_URL="/static/")
    def test_retrieve_full_url_local(self):
        from django.conf import settings
        print "Test generating full url local"
        url = retrieve_full_url("someimage.png")
        self.assertEqual(settings.STATIC_URL, "/static/")
        self.assertEqual("/static/someimage.png",url)
        print "Test passed"

    @override_settings(STATIC_URL="http://s-staging.apprl.com/")
    def test_retrieve_static_url(self):
        from django.conf import settings
        print "Test full static url"
        url = retrieve_static_url("someimage.png")
        self.assertEqual(settings.STATIC_URL, self.temp_static_url)
        self.assertEqual("http://s-staging.apprl.com/static/email/someimage.png",url)
        print "Test retrieve static url"

    @override_settings(STATIC_URL="/static/")
    def test_retrieve_static_url_local(self):
        from django.conf import settings
        print "Test full static url local"
        self.assertEqual(settings.STATIC_URL, "/static/")
        url = retrieve_static_url("someimage.png")
        self.assertEqual("/static/email/someimage.png",url)
        print "Test retrieve static url"

    @override_settings(STATIC_URL="http://s-staging.apprl.com/")
    def test_retrieve_look_full_url(self):
        from django.conf import settings
        look = Look()
        look.name = "yekshamesh"
        look.slug = "yekshamesh"
        #self.assertEqual("/en/look/yekshamesh/",reverse("look-detail",{"slug":look.get_absolute_url()})
        self.assertEqual("/looks/yekshamesh/",look.get_absolute_url())
        print "Test full url"
        domain = Site.objects.get_current().domain
        url = retrieve_full_url(look.get_absolute_url())
        self.assertEqual(settings.STATIC_URL, self.temp_static_url)
        url = 'http://%s%s' % (domain, look.get_absolute_url())
        self.assertEqual("http://example.com/looks/yekshamesh/",url)
        print "Test retrieve static url look suceeded"

