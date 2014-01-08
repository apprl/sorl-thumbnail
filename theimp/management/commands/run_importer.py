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
    )

    def handle(self, *args, **options):
        Importer().run(dry=options.get('dry', False))
