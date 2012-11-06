from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db import connections, models
from django.db.models.loading import get_model

def currency_exchange(to_currency, from_currency):
    """
    Return exchange rate.
    """
    if from_currency == to_currency:
        return 1

    rates = cache.get(settings.APPAREL_RATES_CACHE_KEY)
    if not rates:
        fxrate_model = get_model('importer', 'FXRate')
        rates = {}
        for rate_obj in fxrate_model.objects.filter(base_currency=settings.APPAREL_BASE_CURRENCY):
            rates[rate_obj.currency] = rate_obj.rate

        if rates:
            cache.set(settings.APPAREL_RATES_CACHE_KEY, rates, 60*60)

    rate = rates[to_currency] * (1 / rates[from_currency])
    if from_currency == settings.APPAREL_BASE_CURRENCY:
        rate = rates[to_currency]
    elif to_currency == settings.APPAREL_BASE_CURRENCY:
        rate = 1 / rates[from_currency]

    return rate


def get_gender_from_cookie(request):
    """
    Get gender from cookie in a safe way.
    """
    cookie_value = request.COOKIES.get(settings.APPAREL_GENDER_COOKIE, '')
    if cookie_value in ['M', 'W']:
        return cookie_value

    return 'W'

def get_pagination_page(queryset, per_page, page_num, on_ends=2, on_each_side=3):
    """
    Help method around get_pagination that also returns the actual paged result
    """
    paginator = Paginator(queryset, per_page)
    try:
        paged_result = paginator.page(int(page_num))
    except (EmptyPage, InvalidPage):
        paged_result = paginator.page(paginator.num_pages)
    # in case page_num is a str, from request.get.GET('page')
    except ValueError:
        paged_result = paginator.page(1)

    return (paged_result, get_pagination(paged_result.paginator, paged_result.number, on_ends, on_each_side))

def get_pagination(paginator, page_num, on_ends=2, on_each_side=3):
    """
    Get a pagination object that works with the template pagination.html.
    It will return a dict containing left, mid and right, corresponding to the page
    numbers being displayed in the pagination.

    >>> from django.core.paginator import Paginator
    >>> from apparel import views
    >>> p = Paginator(range(22), 2)
    >>> views.get_pagination(p, 3)
    (None, [1, 2, 3, 4, 5, 6], [10, 11])

    >>> views.get_pagination(p, 6)
    (None, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], None)

    >>> views.get_pagination(p, 9)
    ([1, 2], [6, 7, 8, 9, 10, 11], None)

    >>> p = Paginator(range(100), 2)
    >>> views.get_pagination(p, 23)
    ([1, 2], [20, 21, 22, 23, 24, 25, 26], [49, 50])

    >>> views.get_pagination(p, 23, on_ends=5, on_each_side=2)
    ([1, 2, 3, 4, 5], [21, 22, 23, 24, 25], [46, 47, 48, 49, 50])
    """
    if paginator.num_pages <= (on_ends * 2) + (on_each_side * 2):
        left, mid, right = None, paginator.page_range, None
    else:
        left, mid, right = None, None, None

        if page_num <= on_ends + on_each_side + 1:
            mid = range(1, page_num + 1)
        else:
            left = range(1, on_ends + 1)
            mid = range(page_num - on_each_side, page_num + 1)

        if page_num >= paginator.num_pages - (on_ends + on_each_side + 1):
            mid.extend(range(page_num + 1, paginator.num_pages + 1))
        else:
            mid.extend(range(page_num + 1, on_each_side + page_num + 1))
            right = range(paginator.num_pages - on_ends + 1, paginator.num_pages + 1)

    return {
            'left': left, 
            'mid': mid, 
            'right': right
            }

if connections['default'].vendor.startswith('mysql'):
    sql_template = '(%(function)s(%(field)s) / POW(TIMESTAMPDIFF(HOUR, %(field_two)s, NOW()), 1.53))'
else:
    sql_template = '(%(function)s(%(field)s) / POW((EXTRACT(EPOCH FROM NOW () - %(field_two)s) / 3600), 1.53))'

class CountPopularitySQL(models.sql.aggregates.Aggregate):
    sql_function = 'COUNT'
    sql_template = sql_template

class CountPopularity(models.Aggregate):
    name = 'CountPopularity'

    def add_to_query(self, query, alias, col, source, is_summary):
        aggregate = CountPopularitySQL(col,
                                       source=source,
                                       is_summary=is_summary,
                                       **self.extra)
        query.aggregates[alias] = aggregate
