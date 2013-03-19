from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    args = ''
    help = 'Build static brand list'

    def handle(self, *args, **options):
        from apparelrow.apparel.tasks import generate_brand_list_template
        generate_brand_list_template()
