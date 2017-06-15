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
        brands = { b.name: b for b in Brand.objects.all() }
        brand_names = set(Brand.objects.all().values_list('name', flat=True))
        print brands
        for brand in Brand.objects.iterator():
            print brand
            if brand.name.strip() in brands:
                new_brand = brands[brand.name.strip()]
                for p in brand.products.all():
                    print 'Remapping %s to brand %s' % (p, new_brand)
                    p.brand = new_brand
                    p.save()
                brand.delete()
            else:
                brand.save()    # this will cause a strip of leading whitespace

