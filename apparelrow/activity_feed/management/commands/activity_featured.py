from django.core.management.base import BaseCommand

from apparelrow.activity_feed.tasks import featured_activity


class Command(BaseCommand):
    args = ''
    help = 'Update featured activities'

    def handle(self, *args, **options):
        featured_activity(False)
        featured_activity(True)
