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
        'product_detail_fragment': ['id_language', lambda x: x.pk],
        'product_detail_selected_by': ['id_language', lambda x: x.pk],
        'product_detail_metaextra': ['id_language', lambda x: x.pk],
        'product_detail_title': ['id_language', lambda x: x.pk],
        'product_popup': ['id_language', lambda x: x.pk],
        'product_medium': ['id_language', lambda x: x.pk],
        'look_embed_tooltip': ['id_language', lambda x: x.pk],
        'look_product_tooltip': ['id_language', lambda x: x.pk],
        'activity_like_product_header': ['id_language', lambda x: x.pk],
    },
    'VendorProduct': {
        'product_detail_fragment': ['id_language', lambda x: x.product_id],
        'product_detail_selected_by': ['id_language', lambda x: x.product_id],
        'product_detail_metaextra': ['id_language', lambda x: x.product_id],
        'product_detail_title': ['id_language', lambda x: x.product_id],
        'product_popup': ['id_language', lambda x: x.product_id],
        'product_medium': ['id_language', lambda x: x.product_id],
        'look_embed_tooltip': ['id_language', lambda x: x.product_id],
        'look_product_tooltip': ['id_language', lambda x: x.product_id],
        'activity_like_product_header': ['id_language', lambda x: x.product_id],
    },
    'ProductLike': {
        'product_detail_fragment': ['id_language', lambda x: x.product_id],
        'product_detail_likes': ['id_language', lambda x: x.product_id],
        'product_detail_selected_by': ['id_language', lambda x: x.product_id],
        'product_detail_metaextra': ['id_language', lambda x: x.product_id],
        'product_detail_title': ['id_language', lambda x: x.product_id],
        'product_popup': ['id_language', lambda x: x.product_id],
        'product_medium': ['id_language', lambda x: x.product_id],
        'look_embed_tooltip': ['id_language', lambda x: x.product_id],
        'look_product_tooltip': ['id_language', lambda x: x.product_id],
        'user_medium': ['id_language', lambda x: x.user_id],
    },
    'Look': {
        'look_small': ['id_language', lambda x: x.pk],
        'look_small_like': ['id_language', lambda x: x.pk],
        'look_small_like_product': ['id_language', lambda x: x.pk],
        'look_detail': ['id_language', lambda x: x.pk],
        'look_detail_content': ['id_language', lambda x: x.pk],
        'look_detail_metadesc': ['id_language', lambda x: x.pk],
        'look_detail_metaextra': ['id_language', lambda x: x.pk],
        'look_medium': ['id_language', lambda x: x.pk],
        'look_medium_featured': ['id_language', lambda x: x.pk],
        'look_large_content': ['id_language', lambda x: x.pk],
        'look_large_footer': ['id_language', lambda x: x.pk],
        'contest_stylesearch_panel_header': ['id_language', lambda x: x.pk],
    },
    'LookComponent': {
        'look_small': ['id_language', lambda x: x.look_id],
        'look_small_like': ['id_language', lambda x: x.look_id],
        'look_small_like_product': ['id_language', lambda x: x.look_id],
        'look_detail': ['id_language', lambda x: x.look_id],
        'look_detail_content': ['id_language', lambda x: x.look_id],
        'look_detail_metadesc': ['id_language', lambda x: x.look_id],
        'look_detail_metaextra': ['id_language', lambda x: x.look_id],
        'look_medium': ['id_language', lambda x: x.look_id],
        'look_medium_featured': ['id_language', lambda x: x.look_id],
        'look_large_content': ['id_language', lambda x: x.look_id],
        'look_large_footer': ['id_language', lambda x: x.look_id],
    },
    'LookLike': {
        'look_small': ['id_language', lambda x: x.look_id],
        'look_small_like': ['id_language', lambda x: x.look_id],
        'look_small_like_product': ['id_language', lambda x: x.look_id],
        'look_detail_likes': ['id_language', lambda x: x.look_id],
        'look_detail': ['id_language', lambda x: x.look_id],
        'look_detail_content': ['id_language', lambda x: x.look_id],
        'look_detail_metadesc': ['id_language', lambda x: x.look_id],
        'look_detail_metaextra': ['id_language', lambda x: x.look_id],
        'look_medium': ['id_language', lambda x: x.look_id],
        'look_medium_featured': ['id_language', lambda x: x.look_id],
        'look_large_content': ['id_language', lambda x: x.look_id],
        'look_large_footer': ['id_language', lambda x: x.look_id],
        'user_medium': ['id_language', lambda x: x.user_id],
        'contest_stylesearch_panel_header': ['id_language', lambda x: x.look_id],
    }
}

AVAILABLE_GENDERS = ['M', 'W']

def invalidate_model_handler(sender, **kwargs):
    if 'instance' in kwargs:
        instance = kwargs['instance']
    elif 'comment' in kwargs:
        instance = kwargs['comment']

    try:
        for fragment, cache_data in new_template_cache_map[sender.__name__].items():
            if cache_data[0] == 'id_language':
                arguments = [cache_data[1](instance)]
                for language in settings.LANGUAGES:
                    invalidate_template_cache(fragment, arguments + [language[0]])

            elif cache_data[0] == 'id_language_gender':
                arguments = [cache_data[1](instance)]
                for language in settings.LANGUAGES:
                    for gender in AVAILABLE_GENDERS:
                        invalidate_template_cache(fragment, arguments + [language[0]] + [gender])

    except KeyError:
        pass
