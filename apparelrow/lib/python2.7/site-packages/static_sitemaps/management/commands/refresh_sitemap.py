from django.core.management.base import NoArgsCommand
from django.utils import translation

from static_sitemaps import conf
from static_sitemaps.generator import SitemapGenerator

__author__ = 'xaralis'


class Command(NoArgsCommand):
    command = None
    help = 'Generates sitemaps files to a predefined directory.'

    def handle_noargs(self, **options):
        translation.activate(conf.LANGUAGE)
        generator = SitemapGenerator()
        generator.write_index()
        translation.deactivate()
