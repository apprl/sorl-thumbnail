from django.core.management.base import BaseCommand

from apparelrow.apparel.models import VendorCategory

class Command(BaseCommand):
    args = ''
    help = ''
    option_list = BaseCommand.option_list

    def handle(self, *args, **options):
        deleted_count = 0
        for vc in  VendorCategory.objects.filter(category__isnull=True,
                                                 override_gender__isnull=True,
                                                 default_gender__isnull=True).iterator():
            if vc.vendor_products.count() == 0:
                vc.delete()
                deleted_count += 1

        print 'Deleted {0} vendor categories'.format(deleted_count)
