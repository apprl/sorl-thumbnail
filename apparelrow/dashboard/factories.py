import decimal
import factory
from factory import lazy_attribute
from faker import Faker
import datetime as dt
from random import randint
from advertiser.models import Store
from apparelrow.apparel.models import Vendor, ShortDomainLink
from apparelrow.dashboard.models import ClickCost, Sale, Group, Cut, AggregatedData
from apparelrow.profile.models import User


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = "Regular"


class UserFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = User
    first_name = Faker().name().split(" ")[0]
    last_name = Faker().name().split(" ")[1]
    username = factory.Sequence(lambda n: 'username%s' % n)
    email = factory.LazyAttribute(lambda o: '%s@example.org' % o.username)
    last_login = lazy_attribute(lambda o: o.date_joined + dt.timedelta(days=4))
    is_partner = True
    partner_group = factory.SubFactory(GroupFactory)

    @lazy_attribute
    def date_joined(self):
        return dt.datetime.now() - dt.timedelta(days=randint(5, 50))


class VendorFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Vendor
    name = factory.Sequence(lambda n: 'Vendor %s' % n)


class CutFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Cut
    group = factory.SubFactory(GroupFactory)
    vendor = factory.SubFactory(VendorFactory)
    cut = decimal.Decimal(0.67)
    referral_cut = decimal.Decimal(0.15)


class ClickCostFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = ClickCost
    vendor = factory.SubFactory(VendorFactory)


class SaleFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Sale
    id = factory.Sequence(lambda n: '%s' % (n + 1))
    converted_amount = 500
    converted_commission = 50
    status = Sale.CONFIRMED
    paid = Sale.PAID_PENDING


class AggregatedDataFactory(factory.django.DjangoModelFactory):
    id = factory.Sequence(lambda n: '%s' % (n + 1))
    aggregated_from_name = factory.Sequence(lambda n: 'Name %s' % (n + 1))
    aggregated_from_slug = factory.Sequence(lambda n: 'Slug %s' % (n + 1))
    aggregated_from_link = factory.Sequence(lambda n: 'Link %s' % (n + 1))
    aggregated_from_image = factory.Sequence(lambda n: 'Image %s' % (n + 1))

    class Meta:
        model = AggregatedData


class ShortLinkFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = ShortDomainLink
    vendor = factory.SubFactory(VendorFactory)

class StoreFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Store
    identifier = factory.Sequence(lambda n: 'Store %s' % n)
    user = factory.SubFactory(UserFactory)
