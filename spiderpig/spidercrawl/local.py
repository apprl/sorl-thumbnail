# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

import os
from django.conf import settings

IMAGES_STORE = os.path.join(settings.PROJECT_ROOT, 'media', settings.APPAREL_PRODUCT_IMAGE_ROOT)

ITEM_PIPELINES = [
    'spiderpig.spidercrawl.pipelines.CustomImagesPipeline',
    'spiderpig.spidercrawl.pipelines.RequiredFieldsPipeline',
    'spiderpig.spidercrawl.pipelines.PricePipeline',
]