from django.core.management.base import BaseCommand, CommandError

from dashboard.importer.cj import CJImporter
from dashboard.importer.linkshare import LinkshareImporter
from dashboard.importer.zanox import ZanoxImporter

class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'

    def handle(self, *args, **options):
        for row in CJImporter().get_data():
            print row

        for row in LinkshareImporter().get_data():
            print row

        for row in ZanoxImporter().get_data():
            print row
