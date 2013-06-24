from django.core.management.base import BaseCommand, CommandError

from theimp.parser.parser import Parser

class Command(BaseCommand):
    args = ''
    help = 'Run a parser worker'

    def handle(self, *args, **options):
        # TODO: run as a daemon?
        parser = Parser()
        parser.run()
