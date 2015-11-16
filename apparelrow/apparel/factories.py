# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

import factory
from factory import lazy_attribute
from django.db.models import signals, get_model
from apparelrow.apparel import models
from apparelrow.statistics import models as stat_models
import factory.django
from faker import Faker
import datetime as dt
from random import randint

class BrandFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.Brand
    name = factory.Sequence(lambda n: 'Brand %s' % n)


class CategoryFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.Category
    name = factory.Sequence(lambda n: 'Category %s' % n)



#@factory.django.mute_signals(signals.post_delete, signals.post_save)
class ProductFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.Product
    product_name = factory.Sequence(lambda n: 'Crazy Skirt %s' % n)
    slug = factory.Sequence(lambda n: 'crazy-skirt-%s' % n)
    manufacturer = factory.SubFactory(BrandFactory)
    #product_image = factory.django.ImageField(from_path="static/products/",from_file=u'full/21/210ad55035c97924a7186312a4def89bd5e5884a.jpg',color='blue')

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


class VendorFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = get_model('apparel','Vendor')
    name = factory.Sequence(lambda n: 'Vendor %s' % n)
    user = factory.SubFactory(UserFactory)


class VendorProductFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.VendorProduct
    product = factory.SubFactory(ProductFactory)
    vendor = factory.SubFactory(VendorFactory)
    original_price = 20
    original_currency = "SEK"
    discount_price    = 15
    discount_currency = "SEK"
    original_discount_currency = "SEK"
    availability  = 10


class ProductStatFactory(factory.django.DjangoModelFactory):
    action = 'BuyReferral'
    price = 900
    user_id = 1
    page = 'Product'
    ip = '83.250.7.29'
    is_valid = 'True'

    @lazy_attribute
    def created(self):
        return dt.datetime.now() - dt.timedelta(days=randint(5, 50))

    class Meta:
        model = stat_models.ProductStat


class DomainDeepLinkingFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = get_model('apparel','DomainDeepLinking')
    vendor = factory.SubFactory(VendorFactory)


class NellyVendorWithProductFactory(VendorFactory):
    vendorproduct = factory.RelatedFactory(VendorProductFactory,'vendor',
                                            product__product_key='http://nelly.com/se/skor-kvinna/skor/vardagsskor/nike-1013/wmns-nike-air-max-thea-118540-54/',vendor__name='Nelly')


class AsosVendorWithProductFactory(VendorFactory):
    vendorproduct2 = factory.RelatedFactory(VendorProductFactory,'vendor',
                                            product__product_key='http://www.asos.com/ASOS/ASOS-Vest-With-Extreme-Racer-Back/Prod/pgeproduct.aspx?iid=2108486&istCompanyId=07ba9e81-c032-4e26-a4a9-13073b06d73e&istItemId=wrxmwwxlw&istBid=t&channelref=affiliate',vendor__name='Asos')
