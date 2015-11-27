from urlparse import parse_qs, urlsplit, urlunsplit
import json
import decimal
import datetime
import itertools
import urllib
import httplib
import uuid
import logging
import decimal

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator, InvalidPage, PageNotAnInteger, EmptyPage
from django.db import connections, models
from django.db.models.loading import get_model
from django.utils import translation
from django.utils.encoding import smart_str
from django.utils.http import urlencode
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

logger = logging.getLogger("apparel.debug")


def get_ga_cookie_cid(request=None):
    if request:
        cookie = request.COOKIES.get('_ga')
        if cookie:
            cookie_split = cookie.rsplit('.', 2)
            if len(cookie_split) == 3:
                return '%s.%s' % (cookie_split[1], cookie_split[2])

    return str(uuid.uuid4())


def send_google_analytics_event(cid, category, action, label=None, value=None):
    params = {
        'v': 1,
        'tid': settings.GOOGLE_ANALYTICS_UNIVERSAL_ACCOUNT,
        'cid': cid,
        't': 'event',
        'ec': category,
        'ea': action
    }

    if label:
        params['el'] = label

    if value:
        params['ev'] = value

    params = urllib.urlencode(params)
    connection = httplib.HTTPConnection('www.google-analytics.com')
    connection.request('POST', '/collect', params)


def roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    pending = len(iterables)
    nexts = itertools.cycle(iter(it).next for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = itertools.cycle(itertools.islice(nexts, pending))

def get_featured_activity_today():
    """
    Filters activity on featured date and if the user is not hidden.
    """
    today = datetime.date.today()
    # TODO: if no featured date, default to something?

    return get_model('activity_feed', 'Activity').objects.filter(user__is_hidden=False, active=True, featured_date=today)[:3]


# NOT USED
def get_top_looks_in_network(profile, limit=None):
    Follow = get_model('profile', 'Follow')
    Look = get_model('apparel', 'Look')

    user_ids = Follow.objects.filter(user=profile, active=True).values_list('user_follow', flat=True)
    looks = Look.published_objects.distinct().filter(user__in=user_ids).order_by('-popularity', '-created')

    if limit:
        return looks[:limit]

    return looks


# NOT USED
def get_top_products_in_network(profile, limit=None):
    Follow = get_model('profile', 'Follow')
    Product = get_model('apparel', 'Product')

    user_ids = Follow.objects.filter(user=profile, active=True).values_list('user_follow', flat=True)
    products = Product.valid_objects.distinct().filter(likes__active=True, likes__user__in=user_ids).order_by('-popularity')

    if limit:
        return products[:limit]

    return products


def get_product_alternative(product, default=None):
    """
    Return shop url to product alternatives based on color and category.
    """
    from apparelrow.apparel.search import ApparelSearch

    colors_pk = list(map(str, product.options.filter(option_type__name='color').values_list('pk', flat=True)))
    language_currency = settings.LANGUAGE_TO_CURRENCY.get(translation.get_language(), settings.APPAREL_BASE_CURRENCY)
    query_arguments = {'rows': 1, 'start': 0,
                       'fl': 'price,discount_price',
                       'sort': 'price asc, popularity desc, created desc'}
    query_arguments['fq'] = ['availability:true', 'django_ct:apparel.product']
    query_arguments['fq'].append('gender:(%s OR U)' % (product.gender,))
    query_arguments['fq'].append('category:%s' % (product.category_id))
    if colors_pk:
        query_arguments['fq'].append('color:(%s)' % (' OR '.join(colors_pk),))
    search = ApparelSearch('*:*', **query_arguments)
    docs = search.get_docs()
    if docs:
        shop_reverse = 'shop-men' if product.gender == 'M' else 'shop-women'
        shop_url = '%s?category=%s' % (reverse(shop_reverse), product.category_id)
        if colors_pk:
            shop_url = '%s&color=%s' % (shop_url, ','.join(colors_pk))

        price, currency = docs[0].price.split(',')
        rate = currency_exchange(language_currency, currency)
        price = rate * decimal.Decimal(price)
        price = price.quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)

        return (shop_url, price, language_currency)

    return default


def get_brand_and_category(look):
    #XXX: this query might be slow on live
    for c in look.display_components.select_related('product', 'product__category', 'product__category__parent', 'product__manufacturer'):
        if not c.product:
            continue
        singular = None

        if c.product.category:
            if c.product.category.parent and c.product.category.parent.singular_name:
                if c.product.category.parent.singular_name.strip():
                    singular = c.product.category.parent.singular_name
            elif c.product.category.singular_name:
                if c.product.category.singular_name.strip():
                    singular = c.product.category.singular_name

        if singular:
            yield (u'%s - %s' % (singular, c.product.manufacturer), c.product)
        else:
            try:
                yield (u'%s' % (c.product.manufacturer.name,), c.product)
            except:
                yield (u'-', c.product)

def set_query_parameter(url, param_name, param_value):
    """
    Given a URL, set or replace a query parameter and return the modified
    URL.

    >>> set_query_parameter('http://example.com?foo=bar&biz=baz', 'foo', 'stuff')
    'http://example.com?foo=stuff&biz=baz'

    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)

    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))

def remove_query_parameter(url, param_name):
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)

    if param_name in query_params:
        query_params.pop(param_name)

    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


def generate_sid(product_id, target_user_id=0, page='Default'):
    try:
        target_user_id = int(target_user_id)
    except (TypeError, ValueError, AttributeError):
        target_user_id = 0

    try:
        product_id = int(product_id)
    except (TypeError, ValueError, AttributeError):
        product_id = 0

    return smart_str('%s-%s-%s' % (target_user_id, product_id, page))


def parse_sid(sid):
    if sid:
        try:
            target_user_id, rest = sid.split('-', 1)
            try:
                product_id, page = rest.split('-', 1)
                return (int(target_user_id), int(product_id), page)
            except ValueError:
                try:
                    return (int(target_user_id), int(rest), 'Unknown')
                except ValueError:
                    pass
                return (int(target_user_id), 0, rest)
        except ValueError:
            pass

        try:
            return (int(sid), 0, 'Unknown')
        except ValueError:
            pass

    return (0, 0, 'Unknown')


def vendor_buy_url(product_id, vendor, target_user_id=0, page='Default'):
    """
    Append custom SID to every vendor buy URL.
    """
    sid = generate_sid(product_id, target_user_id, page)

    if not vendor or not vendor.buy_url:
        return ''

    url = smart_str(vendor.buy_url)

    try:
        site_vendor = vendor.vendor
    except ObjectDoesNotExist:
        return url

    # Tradedoubler
    if site_vendor.provider == 'tradedoubler':
        url = '%sepi(%s)' % (url, sid)
    # Commission Junction
    elif site_vendor.provider == 'cj':
        url = set_query_parameter(url, 'SID', sid)
    # Zanox
    elif site_vendor.provider == 'zanox':
        url = '%s&zpar0=%s' % (url, sid)
    # Linkshare
    elif site_vendor.provider == 'linkshare':
        url = set_query_parameter(url, 'u1', sid)
    # Affiliate Window
    elif site_vendor.provider == 'affiliatewindow':
        url = set_query_parameter(url, 'clickref', sid)
    # Our network
    elif site_vendor.provider == 'aan':
        url = set_query_parameter(url, 'custom', sid)
    # Default to our own network
    else:
        url = set_query_parameter(url, 'custom', sid)

    return url


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


def exchange_amount(to_currency, from_currency, amount, precision=None, fixed_rate=None):
    if not precision:
        precision = decimal.Decimal('1.00')

    if not fixed_rate:
        fixed_rate = currency_exchange(to_currency, from_currency)

    amount = fixed_rate * decimal.Decimal(amount)
    amount = amount.quantize(precision, rounding=decimal.ROUND_HALF_UP)

    return amount, fixed_rate


def get_gender_url(gender, named_url):
    if gender == 'M':
        return reverse('%s-men' % (named_url,))
    elif gender == 'W':
        return reverse('%s-women' % (named_url,))

    return reverse(named_url)


def select_from_multi_gender(request, gender_key, gender=None, default=None):
    """
    This utility function has two use cases, it either returns a gender from
    the multi gender cookie based on the gender_key or it sets a gender if the
    gender parameter is not None.
    """
    if gender is None:
        gender = request.app_multi_gender.get(gender_key, None)
        if gender is None:
            user_default = 'A'
            if request.user and request.user.is_authenticated() and request.user.gender:
                user_default = request.user.gender

            request.app_multi_gender[gender_key] = gender = default or user_default
    else:
        request.app_multi_gender[gender_key] = gender

    return gender


def get_paged_result(queryset, per_page, page_num):
    paginator = Paginator(queryset, per_page)
    paginator._count = 10000
    try:
        paged_result = paginator.page(page_num)
    except PageNotAnInteger:
        paged_result = paginator.page(1)
    except EmptyPage:
        paged_result = paginator.page(paginator.num_pages)

    #JAS: this field has been used to determine whether or not to display pagination but it was never set
   # logger.info("per pages: %s and page number: %s result: %s" % (len(paged_result.object_list), page_num, per_page * int(page_num)))
   # logger.info("entire queryset is: %s" % len(queryset))
    #FIXME: When this is set to False, the pagination loads for a fraction of a second and seems to fire off two more tequests (next two pages)
    #WTF?!?
    if(len(queryset) > (per_page * int(page_num))):
        paged_result.has_next = True
    else:
        paged_result.has_next = False
    return paged_result


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
    >>> from apparelrow.apparel import views
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



class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        elif isinstance(o, datetime.datetime):
            return o.isoformat()
        elif isinstance(o, datetime.date):
            return o.isoformat()

        return super(CustomEncoder, self).default(o)

class JSONResponse(HttpResponse):
    """
    JSON response class.
    """
    def __init__(self, obj='', json_opts={}, mimetype='application/json', *args, **kwargs):
        super(JSONResponse, self).__init__(json.dumps(obj, cls=CustomEncoder, **json_opts), mimetype, *args, **kwargs)

class JSONPResponse(HttpResponse):
    """
    JSONP response class.
    """
    def __init__(self, obj='', json_opts={}, callback=None, mimetype='application/json', *args, **kwargs):
        if not callback:
            callback = 'callback'

        super(JSONPResponse, self).__init__('%s(%s)' % (callback, json.dumps(obj, cls=CustomEncoder, **json_opts)), mimetype, *args, **kwargs)


def user_is_bot(request):
    return request.user_agent.is_bot or "ELB" in request.user_agent.ua_string

def save_location(request, location):
    request.user.location = location
    request.user.save(update_fields=['location'])

def has_user_location(request):
    return hasattr(request, 'user') and hasattr(request.user, 'location') and request.user.location

def get_location_text(location):
    for key, text in settings.LOCATION_MAPPING_SIMPLE_TEXT:
        if key == location:
            return text
    return None

def get_market_text_array(vendor_markets):
    markets_text = []
    for item in vendor_markets:
        location_text = get_location_text(item)
        if location_text:
            markets_text.append(location_text)
    return markets_text

def generate_countries_text(markets_text):
    if len(markets_text) > 1:
        return " and ".join([", ".join(markets_text[:-1]),markets_text[-1]])
    return ", ".join(markets_text)

def generate_text_for_markets_array(markets_text):
    availability_text = ""
    if len(markets_text) > 0:
        availability_text = "Available in "
        availability_text += generate_countries_text(markets_text)
    return availability_text

def get_availability_text(vendor_markets):
    if vendor_markets:
        markets_text = get_market_text_array(vendor_markets)
        return generate_text_for_markets_array(markets_text)
    return "Available Internationally"

def get_location_warning_text(vendor_markets, user):
    warning_text = ""
    if hasattr(user, 'show_warnings') and user.show_warnings and user.is_partner:
        if vendor_markets and user.location not in vendor_markets:
            markets_text = get_market_text_array(vendor_markets)
            warning_text = "You will only earn money on visitors from %s that click on this product, not from your current location %s." \
                           % (generate_countries_text(markets_text), get_location_text(user.location))
    return warning_text

def get_external_store_commission(stores, product=None):
    store_commission = None
    if len(stores) > 0:
        commission_array = stores[0].commission.split("/")
        standard_from = decimal.Decimal(commission_array[0])
        standard_to = decimal.Decimal(commission_array[1])
        sale = decimal.Decimal(commission_array[2])
        if sale != 0 and product and product.default_vendor.locale_discount_price:
            store_commission = sale / 100
        else:
            standard_from = standard_to if not standard_from else standard_from
            standard_to = standard_from if not standard_to else standard_to
            store_commission = (standard_from + standard_to)/(2*100)
    return store_commission
