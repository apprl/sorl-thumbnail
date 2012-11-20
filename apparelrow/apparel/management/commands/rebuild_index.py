from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apparel.search import clean_index, rebuild_product_index, rebuild_look_index, rebuild_profile_index

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
        make_option('--model',
            action='store',
            dest='model',
            default=False,
            help='Operate only on this model'
        ),
    )

    def handle(self, *args, **options):
        rebuild_map = {
            'look': rebuild_look_index,
            'product': rebuild_product_index,
            'apparelprofile': rebuild_profile_index,
        }

        app_label_map = {
            'look': 'apparel',
            'product': 'apparel',
            'apparelprofile': 'profile',
        }

        if options['model']:
            if options['model'] not in rebuild_map:
                return 'INCORRECT MODEL'

            if options['clean_rebuild']:
                clean_index(app_label_map[options['model']], options['model'])

            rebuild_count = rebuild_map[options['model']]()
            print 'Reindex %s %ss' % (rebuild_count, options['model'])
        else:
            if options['clean_rebuild']:
                clean_index()

            product_count = rebuild_product_index()
            print 'Reindexed %s products' % (product_count,)
            look_count = rebuild_look_index()
            print 'Reindexed %s looks' % (look_count,)
