import datetime

from django.conf import settings
from django.db.models.loading import get_model
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

from apparelrow.apparel.models import Brand, Product


class Command(BaseCommand):
    args = ''
    help = 'Check for brand updates'

    def handle(self, *args, **options):
        """
        Check for brand updates.
        """
        Activity = get_model('activity_feed', 'Activity')
        content_type = ContentType.objects.get_for_model(Product)
        for brand in Brand.objects.iterator():
            last_update = brand.last_update
            if last_update is None:
                last_update = datetime.datetime.now() - datetime.timedelta(days=30)

            product_display = {'M': None, 'W': None, 'U': None}
            product_count = {'M': 0, 'W': 0}
            for product in Product.valid_objects.filter(date_added__gt=last_update,
                                                        manufacturer=brand).order_by('-modified').iterator():
                # Display product per gender
                if product_display.get(product.gender) is None:
                    if product.gender == 'U' :
                        product_display['M'] = product_display['W'] = product
                    else:
                        product_display[product.gender] = product

                # Product count per gender
                elif product.gender == 'M' or product.gender == 'W':
                    product_count[product.gender] += 1
                else:
                    product_count['M'] += 1
                    product_count['W'] += 1

                product.save()

                activity, created = Activity.objects.get_or_create(user=brand.user,
                                                                   verb='add_product',
                                                                   content_type=content_type,
                                                                   object_id=product.pk,
                                                                   defaults={'active': True,
                                                                             'gender': product.gender})
                if not created and activity.active == False:
                    activity.active = True
                    activity.save()

            for gender in ['M', 'W']:
                object_count = product_count.get(gender)
                product = product_display.get(gender)
                if product and object_count > 0:
                    activity, created = Activity.objects \
                                                .get_or_create(user=brand.user,
                                                               verb='agg_product',
                                                               content_type=content_type,
                                                               object_id=product.pk,
                                                               defaults={'active': True,
                                                                         'gender': gender,
                                                                         'object_count': object_count})

            brand.last_update = datetime.datetime.now()
            brand.save()
