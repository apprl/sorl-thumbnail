import datetime

import redis

from django.conf import settings
from django.db.models.loading import get_model
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

from apparelrow.activity_feed.tasks import aggregate

class Command(BaseCommand):
    args = ''
    help = 'Activity rebuild product availability'

    def handle(self, *args, **options):
        Product = get_model('apparel', 'Product')
        content_type = ContentType.objects.get_for_model(Product)
        for product_id in get_model('activity_feed', 'activity').objects.filter(verb__in=['add_product', 'like_product']).values_list('object_id', flat=True):
            try:
                product = Product.objects.get(pk=product_id)
                available = False
                if product.availability and product.default_vendor and product.default_vendor.availability != 0:
                    available = True

                if not available:
                    activity = get_model('activity_feed', 'activity').objects.filter(content_type=content_type, object_id=product_id).update(is_available=False)

            except Product.DoesNotExist:
                print 'failed', product_id
                get_model('activity_feed', 'activity').objects.filter(content_type=content_type, object_id=product_id).delete()
