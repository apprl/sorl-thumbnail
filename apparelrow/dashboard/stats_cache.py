
import redis
from decimal import Decimal
from django.conf import settings
from progressbar import ProgressBar, Percentage, Bar


STATS_TTL = 365 * 25 * 60 * 60


def redis_connection():
    return redis.StrictRedis(host=settings.CELERY_REDIS_HOST,
                             port=settings.CELERY_REDIS_PORT,
                             db=settings.DASHBOARD_STATS_REDIS_DB)


def stats_month_cache(func):
    def wrapper(year, month, *args, **kwargs):
        if not settings.DISABLE_DASHBOARD_STATS_CACHING:
            key = '{}_{}_{}'.format(year, month, func.__name__)
            redis_conn = redis_connection()
            rval = redis_conn.get(key)
            if rval:
                return Decimal(rval)
            fval = func(year, month, *args, **kwargs)
            if fval:
                fval = Decimal(fval)
            else:
                fval = 0
            redis_conn.set(key, fval, STATS_TTL)
            return fval
        else:
            return func(year, month, *args, **kwargs)


    return wrapper


def flush_stats_cache():
    redis_conn = redis_connection()
    redis_conn.flushall()


def flush_stats_cache_by_one_year(year):
    redis_conn = redis_connection()
    keys = redis_conn.keys('{}_*'.format(year))
    if keys:
        redis_conn.delete(*keys)


def flush_stats_cache_by_one_month(year, month):
    redis_conn = redis_connection()
    keys = redis_conn.keys('{}_{}_*'.format(year, month))
    if keys:
        redis_conn.delete(*keys)


# This can take forever.
def warm_cache():
    from apparelrow.dashboard.models import Sale
    years = [d.year for d in Sale.objects.dates('sale_date', 'year')]
    # pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=len(years)*12).start()
    for i, year in enumerate(years):
        for month in range(1, 13):
            # pbar.update(i*12+month)
            warm_cache_by_one_month(year, month)


def warm_cache_by_one_year(year):
    for month in range(1, 13):
        warm_cache_by_one_month(year, month)


def warm_cache_by_one_month(year, month):
    import stats_admin # we need to import it locally to handle circular dependency
    print 'Warming cache', year, month
    print stats_admin.admin_top_stats(year, month)
    stats_admin.admin_clicks(year, month)
    stats_admin.ppc_all_stores_stats(year, month)

