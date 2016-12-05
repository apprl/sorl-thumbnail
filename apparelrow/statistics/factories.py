import factory

from apparelrow.apparel.models import ShortStoreLink, ShortDomainLink, DomainDeepLinking
from apparelrow.statistics import models as stat_models
from django.db.models import get_model
from faker import Faker
from factory import lazy_attribute
import datetime as dt
from random import randint


class UserFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = get_model('profile','User')
    first_name = Faker().name().split(" ")[0]
    last_name = Faker().name().split(" ")[1]
    username = factory.Sequence(lambda n: 'username%s' % n)
    email = factory.LazyAttribute(lambda o: '%s@example.org' % o.username)
    last_login = lazy_attribute(lambda o: o.date_joined + dt.timedelta(days=4))

    @lazy_attribute
    def date_joined(self):
        return dt.datetime.now() - dt.timedelta(days=randint(5, 50))


class BrandFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = get_model('apparel','Brand')
    name = factory.Sequence(lambda n: 'Brand %s' % n)


class VendorFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = get_model('apparel','Vendor')


class ProductFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = get_model('apparel', 'Product')
    product_name = factory.Sequence(lambda n: 'Crazy Skirt %s' % n)
    slug = factory.Sequence(lambda n: 'crazy-skirt-%s' % n)
    manufacturer = factory.SubFactory(BrandFactory)


class VendorProductFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = get_model('apparel','VendorProduct')
    product = factory.SubFactory(ProductFactory)
    vendor = factory.SubFactory(VendorFactory)
    original_price = 20
    original_currency = "SEK"
    discount_price = 15
    discount_currency = "SEK"
    original_discount_currency = "SEK"
    availability = 10


class ProductStatFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = stat_models.ProductStat
    action = 'BuyReferral'
    price = 900
    user_id = 1
    page = 'Product'


class ShortStoreLinkFactory(factory.django.DjangoModelFactory):
    vendor = factory.SubFactory(VendorFactory)

    class Meta:
        model = ShortStoreLink


class ShortDomainLinkFactory(factory.django.DjangoModelFactory):
    url = "" # Should be supplied
    vendor = factory.SubFactory(VendorFactory)
    user = factory.SubFactory(UserFactory)
    created = dt.datetime.today()

    class Meta:
        model = ShortDomainLink


class DomainDeepLinkingFactory(factory.django.DjangoModelFactory):
    vendor = factory.SubFactory(VendorFactory)
    domain = "" # Should be supplied
    template = factory.LazyAttribute(lambda o: "http://apprl.com/a/link/?store_id=%s&custom={sid}&url={url}" % o.vendor.name.lower())

    class Meta:
        model = DomainDeepLinking