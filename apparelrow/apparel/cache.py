import hashlib

from django.conf import settings
from django.core.cache import cache
from django.utils.http import urlquote

def invalidate_template_cache(fragment_name, variables):
    """
    Stolen from Michael Malone's django-caching:
    Explicitly set a None value instead of just deleting so we don't have any race
    conditions where:
    Thread 1 -> Cache miss, get object from DB
    Thread 2 -> Object saved, deleted from cache
    Thread 1 -> Store (stale) object fetched from DB in cache
    Five second should be more than enough time to prevent this from happening for
    a web app.
    """
    args = hashlib.md5(u':'.join([urlquote(var) for var in variables]))
    cache_key = 'template.cache.%s.%s' % (fragment_name, args.hexdigest())
    cache.set(cache_key, None, 2)

new_template_cache_map = {
    'Product': {
        'products_sidebar': ['id_language', lambda x: x.pk],
        'product_detail_fragment': ['id_language', lambda x: x.pk],
        'product_shop': ['id_language', lambda x: x.pk],
        'product_thumb': ['id_language', lambda x: x.pk],
    },
    'VendorProduct': {
        'products_sidebar': ['id_language', lambda x: x.product_id],
        'product_detail_fragment': ['id_language', lambda x: x.product_id],
        'product_shop': ['id_language', lambda x: x.product_id],
        'product_thumb': ['id_language', lambda x: x.product_id], # not sure if needed
    },
    'Look': {
        'look_widget': ['id_language', lambda x: x.pk],
        'look_wide': ['id_language', lambda x: x.pk],
        'look_small': ['id_language', lambda x: x.pk],
        'look_small_like': ['id_language', lambda x: x.pk],
        'look_detail1': ['id_language', lambda x: x.pk],
        'look_detail2': ['id_language', lambda x: x.pk],
        'look_detail3': ['id_language', lambda x: x.pk],
    },
    'LookComponent': {
        'look_widget': ['id_language', lambda x: x.look_id],
        'look_wide': ['id_language', lambda x: x.look_id],
        'look_small': ['id_language', lambda x: x.look_id],
        'look_small_like': ['id_language', lambda x: x.look_id],
        'look_detail1': ['id_language', lambda x: x.look_id],
        'look_detail2': ['id_language', lambda x: x.look_id],
        'look_detail3': ['id_language', lambda x: x.look_id],
    },
}

AVAILABLE_GENDERS = ['M', 'W']

def invalidate_model_handler(sender, **kwargs):
    try:
        for fragment, cache_data in new_template_cache_map[sender.__name__].items():
            if cache_data[0] == 'id_language':
                arguments = [cache_data[1](kwargs['instance'])]
                for language in settings.LANGUAGES:
                    invalidate_template_cache(fragment, arguments + [language[0]])

            elif cache_data[0] == 'id_language_gender':
                arguments = [cache_data[1](kwargs['instance'])]
                for language in settings.LANGUAGES:
                    for gender in AVAILABLE_GENDERS:
                        invalidate_template_cache(fragment, arguments + [language[0]] + [gender])

    except KeyError:
        pass
