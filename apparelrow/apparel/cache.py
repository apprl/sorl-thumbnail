from django.conf import settings
from django.core.cache import cache
from django.utils.hashcompat import md5_constructor
from django.utils.http import urlquote

def invalidate_cache(cache_key):
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
  cache.set(cache_key, None, 2)

def invalidate_template_cache(fragment_name, *variables):
  args = md5_constructor(u':'.join([urlquote(var) for var in variables]))
  cache_key = 'template.cache.%s.%s' % (fragment_name, args.hexdigest())
  invalidate_cache(cache_key)


template_cache_map = {
    'Product':  (
        'product_detail_fragment1', 'product_detail_fragment2',
        'product_small', 'product_thumb', 'look_widget', 'look_small', 'look_small_like',
    ),
    'VendorProduct': (
        'product_detail_fragment1', 'product_detail_fragment2',
        'look_widget', 'look_small', 'look_small_like',
    ),
    'VendorProductVariation': (  # Fixme: Validate these
        'product_detail_fragment1', 'product_detail_fragment2',
        'look_widget', 'look_small', 'look_small_like',
    ),
    'Option': (
        'filter_menu',
    ),
    'Category': (
        'filter_menu',
    ),
    'Look': (
        'look_detail1', 'look_detail2', 'look_detail3', 'look_small_like',
        'look_widget', 'look_small',
        'index', 'index_looks'
    ), # < only if featured was changed
    'LookComponent': (
        'look_detail1', 'look_detail2', 'look_detail3', 'look_widget', 'look_small', 'look_small_like',
    ),
    'FirstPageContent': (
        'index'
    ),
}

class_level_map = (
    'filter_menu',
    'index',
    'index_looks'
)


def invalidate_model_handler(sender, **kwargs):
    try:
        for fragment in template_cache_map[sender.__name__]:
            cache_args = [] if fragment in class_level_map else [kwargs['instance'].id]
            
            for lang in settings.LANGUAGES:
                temp_cache_args = cache_args + [lang[0]]
                invalidate_template_cache(fragment, *temp_cache_args)
    
    except KeyError, e:
        pass
    

