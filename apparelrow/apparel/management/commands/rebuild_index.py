from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apparelrow.apparel.search import clean_index, rebuild_product_index, rebuild_look_index, rebuild_user_index

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
        make_option('--host',
            action='store',
            dest='host',
            default=None,
            help='Rebuild solr on this host'
        ),
        make_option('--vendor_id',
            action='store',
            dest='vendor_id',
            default=None,
            help='Isolate rebuild for this vendor(id). Only supported for products.'
        ),
    )

    def handle(self, *args, **options):
        rebuild_map = {
            'look': rebuild_look_index,
            'product': rebuild_product_index,
            'user': rebuild_user_index,
        }

        app_label_map = {
            'look': 'apparel',
            'product': 'apparel',
            'user': 'profile',
        }

        url = None
        host = options.get('host')
        if host:
            url = 'http://{0}:8983/solr'.format(host)

        if options['model']:
            if options['model'] not in rebuild_map:
                return 'INCORRECT MODEL'

            if options['clean_rebuild']:
                clean_index(app_label_map[options['model']], options['model'], url=url)

            if options['model'] == 'product':
                rebuild_count = rebuild_map[options['model']](url=url,vendor_id=options.get('vendor_id',None))
            else:
                rebuild_count = rebuild_map[options['model']](url=url)
            print 'Reindex %s %ss' % (rebuild_count, options['model'])
        else:
            if options['clean_rebuild']:
                clean_index(url=url)

            product_count = rebuild_product_index(url=url)
            print 'Reindexed %s products' % (product_count,)

            look_count = rebuild_look_index(url=url)
            print 'Reindexed %s looks' % (look_count,)

            user_count = rebuild_user_index(url=url)
            print 'Reindexed %s users' % (user_count,)
