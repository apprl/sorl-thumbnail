import itertools

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.cache import get_cache
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        cache = get_cache('nginx')

        # Empty shop embed
        for user_id in get_user_model().objects.values_list('pk', flat=True):
            for x in itertools.product((x[0] for x in settings.LANGUAGES), ['A', 'M', 'W']):
                key = reverse('shop-embed', args=[user_id, x[0], x[1]])
                cache.delete(key)
                print 'Deleting %s' % key

        # Empty look embed
        for look_slug in get_model('apparel', 'Look').objects.values_list('slug', flat=True):
            cache.delete(reverse('look-embed', args=[look_slug]))
            for look_embed in get_model('apparel', 'LookEmbed').objects.filter(look__slug=look_slug):
                key = reverse('look-embed-identifier', args=[look_embed.identifier, look_slug])
                cache.delete(key)
                print 'Deleting %s' % key
