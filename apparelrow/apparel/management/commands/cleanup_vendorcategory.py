from optparse import make_option

from django.core.management.base import BaseCommand
from apparelrow.apparel.models import VendorCategory
from progressbar import ProgressBar, Percentage, Bar

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
        make_option('--clean',
            action='store_true',
            dest='clean',
            default=False,
            help='Cleans out the Vendor Categories from the database.',
        ),
        make_option('--verbose',
            action='store_true',
            dest='verbose',
            default=False,
            help='Shows a progress bar.',
        ),
    )

    def handle(self, *args, **options):
        deleted_count = 0
        vcs = VendorCategory.objects.filter(category__isnull=True,override_gender__isnull=True,default_gender__isnull=True)
        pbar = None
        if not vcs.count() > 0:
            print "No vendor categories to clean out."
            return

        if options["verbose"]:
            pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=vcs.count()).start()

        for index, vc in enumerate(vcs.iterator()):
            if pbar:
                pbar.update(index)
            if options['delete_unmapped'] or vc.vendor_products.count() == 0:
                if options['clean']:
                    vc.delete()
                deleted_count += 1
        if pbar:
            pbar.finish()
        print 'Deleted [{}] {} vendor categories'.format(options['clen'], deleted_count)
