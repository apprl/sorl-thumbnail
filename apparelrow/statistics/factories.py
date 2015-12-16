import factory
from apparelrow.statistics import models as stat_models
from django.db.models import get_model


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
