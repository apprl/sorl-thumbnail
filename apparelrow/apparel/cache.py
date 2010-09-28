from django.core.cache import cache
from django.utils.hashcompat import md5_constructor
from django.utils.http import urlquote

def invalidate_cache(self, cache_key):
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
