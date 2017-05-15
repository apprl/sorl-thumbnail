import logging
import pickle
import time
from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from redis import StrictRedis

log = logging.getLogger(__name__)

STATS_TTL = 365 * 25 * 60 * 60

redis = StrictRedis(host=settings.CELERY_REDIS_HOST, port=settings.CELERY_REDIS_PORT, db=settings.DASHBOARD_STATS_REDIS_DB)

# Utility range functions
# Djangos range filter maps to BETWEEN which is inclusive so we need to subract a small amount so we stay within the month

all_time = [datetime(1990, 1, 1), datetime(2999, 1, 1)]

def yrange(year):
    start = datetime(year, 1, 1)
    end = start + relativedelta(years=1) - relativedelta(microseconds=1)
    return [start, end]


def mrange(year, month):
    start = datetime(year, month, 1)
    end = start + relativedelta(months=1) - relativedelta(microseconds=1)
    return [start, end]


def drange(year, month, day):
    start = datetime(year, month, day)
    end = start + relativedelta(days=1) - relativedelta(microseconds=1)
    return [start, end]


# Function wrapper that caches time range functions. It uses args & kwargs in cache key.

def stats_cache(func):
    def check_time_range(time_range):
        if not isinstance(time_range, (tuple, list)) or len(time_range) != 2 \
                or time_range[0] < all_time[0] or time_range[1] > all_time[1]:
            raise ValueError("time_range outside bounds: %s" % all_time)

    def wrapper(time_range, *args, **kwargs):
        # this gives us the option to bypass the cache completely
        if not settings.ENABLE_DASHBOARD_STATS_CACHING:
            return func(time_range, *args, **kwargs)

        check_time_range(time_range)
        key = cache_key(time_range, func.__name__, *args, **kwargs)

        # try to get it from the cache
        hit = redis.get(key)
        if hit:
            data = pickle.loads(hit)
            return data['val']

        # otherwise, execute function and set cache
        start = time.time()
        val = func(time_range, *args, **kwargs)
        end = time.time()

        add_to_stats_cache(time_range, key, pickle.dumps(dict(
            val=val,
            when=datetime.now(),
            exec_time_secs=end-start
        )))
        return val
    return wrapper


def cache_key(time_range, func_name, *args, **kwargs):
    key = 'stats_{}__{}'.format(str(time_range[0]) + '::' + str(time_range[1]), func_name)
    try:
        key += '__{}'.format(str(args))
    except:
        raise Exception("Don't pass any args that can't be turned into strings")
    try:
        key += '__{}'.format(str(kwargs))
    except:
        raise Exception("Don't pass any kwargs that can't be turned into strings")
    return key


"""
To make this work we to store three things:
    1) The value itself. Key is what cache_key function returns
    2) time_range[0] - start of the time range. Score is unix timestamp. Value is cache_key
    3) time_range[1] - end of the time range. Score is unix timestamp. Value is cache_key

We do this so that we can invalidate parts of the cache based on arbitrary time ranges. To do that
we need to calculate the intersection of the ranges. It's a little tricky because we couldn't express
the logic using standards redis ops so we had to write a little custom lua.

If zrevrangebyscore ever gets a store option we might be able to get rid of the lua:
https://github.com/antirez/redis/issues/678
"""
def add_to_stats_cache(time_range, key, val):
    pipe = redis.pipeline()
    # delete before we add just to make sure we don't get inconsistencies
    pipe.delete(key)
    pipe.zrem('stats_ranges_left', key)
    pipe.zrem('stats_ranges_right', key)
    pipe.set(key, val)
    pipe.zadd('stats_ranges_left', time_range[0].strftime("%s"), key)
    pipe.zadd('stats_ranges_right', time_range[1].strftime("%s"), key)
    pipe.execute()


def flush_stats_cache():
    flush_stats_cache_by_range(all_time)


def flush_stats_cache_by_year(year):
    flush_stats_cache_by_range(yrange(year))


def flush_stats_cache_by_month(year, month):
    flush_stats_cache_by_range(mrange(year, month))


def flush_stats_cache_by_day(year, month, day):
    flush_stats_cache_by_range(drange(year, month, day))


lua_invalidate = redis.register_script(
    """
    local function create_zrange_subset(from_set, to_set, from_i, to_i)
        local t = redis.call('zrangebyscore', from_set, from_i, to_i, 'withscores')
        local i=1
        while(i<=#t) do
            redis.call('zadd', to_set, t[i+1], t[i])
            i=i+2
        end
        return to_set
    end

    local function perform_set_op_and_delete_elements(op, left_from, left_to, right_from, right_to)
        redis.call('del', 'stats_left_subset', 'stats_right_subset', 'stats_keys_to_be_removed')

        -- select subsets from ranges and store them
        create_zrange_subset('stats_ranges_left', 'stats_left_subset', left_from, left_to)
        create_zrange_subset('stats_ranges_right', 'stats_right_subset', right_from, right_to)

        -- perform union / intersection between the subsets
        redis.call(op, 'stats_keys_to_be_removed', 2, 'stats_left_subset', 'stats_right_subset')

        -- remove keys
        local t = redis.call('zrangebyscore', 'stats_keys_to_be_removed', 0, 'inf')
        local i=1
        while(i<=#t) do
            redis.call('del', t[i])
            redis.call('zrem', 'stats_ranges_left', t[i])
            redis.call('zrem', 'stats_ranges_right', t[i])
            i=i+1
        end
    end

    -- this will find any cached ranges within or intersecting this
    local function invalidate_intersecting(range_start, range_end)
        perform_set_op_and_delete_elements('zunionstore', range_start, range_end, range_start, range_end)
    end

    -- this will find any ranges that contain this
    local function invalidate_wrapping(range_start, range_end)
        perform_set_op_and_delete_elements('zinterstore', 0, range_start, range_end, 'inf')
    end

    -- take keys parameters from lua_invalidate()
    invalidate_intersecting(KEYS[1], KEYS[2])
    invalidate_wrapping(KEYS[1], KEYS[2])
    """
)


def flush_stats_cache_by_range(time_range):
    lua_invalidate(keys=[time_range[0].strftime("%s"), time_range[1].strftime("%s")])



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
    from apparelrow.dashboard.stats import stats_admin
    stats_admin.admin_clicks(year, month)
    stats_admin.ppc_all_stores_stats(year, month)

