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
  cache.set(cache_key, None, 5)

def invalidate_template_cache(fragment_name, *variables):
  args = md5_constructor(u':'.join([urlquote(var) for var in variables]))
  cache_key = 'template.cache.%s.%s' % (fragment_name, args.hexdigest())
  invalidate_cache(cache_key)




template_cache_map = {
    'Product':  (
        'product_detail1', 'product_detail2', 'product_search', 
        'product_small', 'product_thumb', 'look_widget', 'look_small',
    ),
    'VendorProduct': (
        'product_detail1', 'product_detail2', 'product_search', 
        'look_widget', 'look_small',
    ),
    'VendorProductVariation': (
        'product_detail1', 'product_detail2', 'product_search', 
        'look_widget', 'look_small',
    ),
    'Option': (
        'filter_menu',
    ),
    'Category': (
        'filter_menu',  
    ),
    'Look': (
        'look_detail', 'look_small', 'product_detail', 'look_widget', 'look_small',
        'index',
    ), # < only if featured was changed
    'LookComponent': (
        'look_detail', 'look_widget', 'look_small',
    ),
}


def invalidate_model_handler(sender, **kwargs):
    if kwargs['created']:
        return
    
    try:
        for fragment in template_cache_map[sender.__name__]:
            for lang in settings.LANGUAGES:
                invalidate_template_cache(fragment, kwargs['instance'].id, lang[0])
    
    except KeyError, e:
        pass
    

