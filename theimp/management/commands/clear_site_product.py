import json
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db.models.loading import get_model

from theimp.utils import ProductItem

# Not sure why this method would be needed at all. Command resets the site_product key which is needed
# to connect the imp Product with the corresponding apparel Product
class Command(BaseCommand):
    args = ''
    help = 'Clear site product'
    option_list = BaseCommand.option_list + (
        make_option('--vendor',
            action='store',
            dest='vendor',
            default=None,
            help='Run only this vendor',
        ),
    )

    def handle(self, *args, **options):
        vendor = get_model('theimp', 'Vendor').objects.get(name=options.get('vendor'))
        products = get_model('theimp', 'Product').objects.filter(vendor__name=options.get('vendor'))
        for product in products:
            item = ProductItem(product)
            item.set_site_product(None)
            product.json = json.dumps(item.data)
            product.save()
