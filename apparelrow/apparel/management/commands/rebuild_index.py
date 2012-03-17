from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apparel.search import clean_index, rebuild_product_index, rebuild_look_index

class Command(BaseCommand):
    args = ''
    help = 'Rebuild the search index'
    option_list = BaseCommand.option_list + (
        make_option('--clean',
            action='store_true',
            dest='clean_rebuild',
            default=False,
            help='Delete indexes and start from a clean index'
        ),
    )

    def handle(self, *args, **options):
        if options['clean_rebuild']:
            clean_index()

        rebuild_product_index()
        rebuild_look_index()
