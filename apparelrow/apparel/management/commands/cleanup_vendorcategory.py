from optparse import make_option

from django.core.management.base import BaseCommand

from apparelrow.apparel.models import VendorCategory


class Command(BaseCommand):
    args = ''
    help = ''
    option_list = BaseCommand.option_list + (
        make_option('--delete-unmapped',
            action='store_true',
            dest='delete_unmapped',
            default=False,
            help='Delete unmapped vendor categories',
        ),
    )

    def handle(self, *args, **options):
        deleted_count = 0
        for vc in  VendorCategory.objects.filter(category__isnull=True,
                                                 override_gender__isnull=True,
                                                 default_gender__isnull=True).iterator():
            if vc.vendor_products.count() == 0 or options['delete_unmapped']:
                vc.delete()
                deleted_count += 1

        print 'Deleted {0} vendor categories'.format(deleted_count)
