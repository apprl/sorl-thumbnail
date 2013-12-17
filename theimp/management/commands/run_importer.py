from django.core.management.base import BaseCommand, CommandError

from theimp.importer import Importer


class Command(BaseCommand):
    args = ''
    help = 'Importer worker'

    def handle(self, *args, **options):
        # TODO: run as a daemon?
        Importer().run()
