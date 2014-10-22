import re

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from apparelrow.apparel.models import Product, ProductLike
from apparelrow.profile.models import User
from apparelrow.dashboard.models import Group
from django.test import Client

from localeurl.utils import locale_url

def reverse_locale(*args, **kwargs):
    return locale_url(reverse(*args, **kwargs), 'en')


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestProfile(TransactionTestCase):
    def test_signup(self):
        c = Client()
        response = c.post(reverse_locale('auth_register_email'), {'first_name': 'test',
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

class TestProfileLikes(TestCase):
    def setUp(self):
        owner_user = User.objects.create(name="Metro Test", username="owner", slug="owner", is_active=True, email="owner@test.com")
        group = Group.objects.create(name="Group Test", owner=owner_user)
        user_test = User.objects.create(name="Blogger Test", username="usertest", slug="user_test",
                                        email="user@test.com", partner_group=group, is_active=True)
        user_test.set_password("1234qwer")
        user_test.save()

    def test_product_like_group_partner(self):
        """
            Tests if an user likes a product and belongs to a partner group and it's not the owner, the owner of that
            partner group will automatically like the product also
        """
        product = Product.objects.create(slug="product_test", static_brand="testbrand", sku="testsku")
        owner_user = User.objects.get(email="owner@test.com")

        # 'User owns group' relation is One-To-One
        group = Group.objects.get(owner=owner_user)

        user = User.objects.get(email="user@test.com")
        self.assertTrue(user.is_active)

        login = self.client.login(username="usertest", password="1234qwer")
        self.assertTrue(login)

        response = self.client.post(reverse('product-action', kwargs={'pk': product.id,'action':'like'}))
        self.assertEqual(response.status_code, 200)

        user_like = ProductLike.objects.filter(user=user, product=product)
        self.assertEqual(len(user_like), 1)
        self.assertTrue(user_like[0].active)

        owner_like = ProductLike.objects.filter(user=owner_user, product=product)
        self.assertEqual(len(owner_like), 1)
        self.assertTrue(owner_like[0].active)

    def test_product_unlike_group_partner(self):
        """
            Tests if an user unlikes a product and belongs to a partner group and it's not the owner, the owner of that
            partner group will automatically unlike the product also
        """
        product = Product.objects.create(slug="product_test", static_brand="testbrand", sku="testsku")
        owner_user = User.objects.get(email="owner@test.com")

        # 'User owns group' relation is One-To-One
        group = Group.objects.get(owner=owner_user)

        user = User.objects.get(email="user@test.com")
        login = self.client.login(username="usertest", password="1234qwer")
        self.assertTrue(login)

        response = self.client.post(reverse('product-action', kwargs={'pk': product.id,'action':'unlike'}))
        self.assertEqual(response.status_code, 200)

        user_like = ProductLike.objects.filter(user=user, product=product)
        self.assertEqual(len(user_like), 1)
        self.assertFalse(user_like[0].active)

        owner_like = ProductLike.objects.filter(user=owner_user, product=product)
        self.assertEqual(len(owner_like), 1)
        self.assertFalse(owner_like[0].active)