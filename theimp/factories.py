# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

import factory
from factory import lazy_attribute
from django.db.models import signals, get_model
from theimp import models
from apparelrow.statistics import models as stat_models
import factory.django
from faker import Faker
import datetime as dt
from random import randint
import simplejson

class VendorFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.Vendor
    name = factory.Sequence(lambda n: 'ImpVendor %s' % n)

# @factory.django.mute_signals(signals.post_delete, signals.post_save)
class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Product

    json = simplejson.loads(u"{\"final\": [\"white\", \"beige\"], \"brand_id\": 117}")
    vendor = factory.SubFactory(VendorFactory)

