from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from theimp.importer import Importer


class Command(BaseCommand):
    args = ''
    help = 'Importer worker'
    option_list = BaseCommand.option_list + (
        make_option('--dry',
            action='store_true',
            dest='dry',
            default=False,
            help='Dry run, do not updated any products',
        ),
        make_option('--vendor',
            action='store',
            dest='vendor',
            default=None,
        ),
        make_option('--force',
            action='store_true',
            dest='force',
            default=False,
        ),
    )

    def handle(self, *args, **options):
        Importer().run(dry=options.get('dry', False), vendor=options.get('vendor'),force=options.get('force', False))
