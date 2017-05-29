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
from apparelrow.statistics import models as stat_models
from apparelrow.statistics.factories import UserFactory

class ProductStatFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = stat_models.ProductStat
    action = 'BuyReferral'
    price = 900
    user_id = 1
    page = 'Product'

class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = "Regular"


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
