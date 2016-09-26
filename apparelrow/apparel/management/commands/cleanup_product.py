import datetime
from optparse import make_option
from django.contrib.comments import Comment
from django.core.management.base import BaseCommand
from sorl.thumbnail import default
from apparelrow.apparel.models import Product, ProductLike, LookComponent, ShopProduct, ProductWidgetProduct, \
    ShortProductLink, VendorProduct
from progressbar import ProgressBar, Percentage, Bar
from apparelrow.dashboard.models import Sale
from apparelrow.statistics.models import ProductClick, ProductStat


class Command(BaseCommand):
    args = ''
    help = ''

    option_list = BaseCommand.option_list + (
            make_option('--clean',
                action='store_true',
                dest='clean',
                default=False,
                help='Cleans out the Products from the database.',
            ),
            make_option('--verbose',
                action='store_true',
                dest='verbose',
                default=False,
                help='Shows a progress bar.',
            ),
              make_option('--batch-size',
                action='store',
                dest='batch',
                default=10000,
                help='The amount of products to check in this batch',
            ),
              make_option('--offset',
                action='store',
                dest='offset',
                default=0,
                help='Product offset',
            ),
            make_option('--desc',
                action='store_true',
                dest='desc',
                default=False,
                help='Sorting ',
            ),
            make_option('--product_id',
                        action='store',
                        dest='product_id',
                        default=0,
                        help='Targeting one product for evaluation purposes',
                        ),
    )
    def handle(self, *args, **options):
        deleted_count = 0
        pbar = None
        from decimal import Decimal
        six_months_ago = datetime.datetime.today() - datetime.timedelta(days=30*6)
        print "Running job for date {}".format(six_months_ago)
        offset = int(options["offset"])
        batch = int(options["batch"])
        sort = "-id" if options["desc"] else "id"
        product_id = int(options.get("product_id", 0))
        if not product_id:
            filters = {"availability":False, "modified__lte": six_months_ago}
        else:
            filters = {"id__in": [product_id]}

        products = Product.objects.filter(**filters).order_by(sort)[offset:offset+batch]
        product_count = products.count()
        if not product_count > 0:
            print "No products to clean out."
            return

        if options["verbose"]:
            pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=products.count()).start()

        print 'About to check {} products'.format(product_count)
        checks = [("ProductLike", lambda x: ProductLike.objects.filter(product=x).exists()),
                  ("LookComponent", lambda x: LookComponent.objects.filter(product=x).exists()),
                  ("ShopProduct", lambda x: ShopProduct.objects.filter(product=x).exists()),
                  ("ProductWidgetProduct", lambda x: ProductWidgetProduct.objects.filter(product=x).exists()),
                  ("ShortProductLink", lambda x: ShortProductLink.objects.filter(product=x).exists()),
                  ("ProductClick", lambda x: ProductClick.objects.filter(product=x).exists()),
                  ("Sale", lambda x: Sale.objects.filter(product_id=x.id).exists()),
                  ("Comment", lambda x: Comment.objects.filter(content_type__name="product", object_pk=x.id).exists()),
                  ("ProductStat", lambda x: ProductStat.objects.filter(vendor=x.default_vendor.vendor.name, product=x.slug).exists()),
                  ]

        for index, product in enumerate(products.iterator()):
            if pbar:
                pbar.update(index)

            delete = True
            vendor_exists = VendorProduct.objects.filter(product=product).exists()
            if vendor_exists:
                for name, check in checks:
                    if check(product):
                        print "Product: {}:{} has more than one entry in {}".format(product.id, product, name)
                        delete = False
                        break
            if not delete:
                continue
            else:
                deleted_count += 1
                if options["clean"]:
                    product.delete()

        """if ProductLike.objects.filter(product=product.id).count() == 0 and LookComponent.objects.filter(product=product_id).count() == 0:
            if options["clean"]:
                product.delete()
            deleted_count += 1
        else:
            print 'Could not delete {}'.format(product)
        """
        if pbar:
            pbar.finish()
        print 'Deleted {}/{} products'.format(deleted_count, product_count)
