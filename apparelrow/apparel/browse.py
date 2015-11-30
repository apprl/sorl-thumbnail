import decimal
import json
import logging

from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.conf import settings
from django.shortcuts import render_to_response
from django.shortcuts import render
from django.db.models.loading import get_model
from django.template import RequestContext
from django.template import loader
from django.core.cache import get_cache
from django.core.paginator import EmptyPage
from django.core.urlresolvers import reverse
from django.utils import translation
from django.utils.translation import get_language, ugettext as _, ungettext
from django.contrib.auth.decorators import login_required

from apparelrow.apparel.search import PRODUCT_SEARCH_FIELDS
from apparelrow.apparel.search import ApparelSearch
from apparelrow.apparel.models import Brand
from apparelrow.apparel.models import Option
from apparelrow.apparel.models import Category
from apparelrow.apparel.models import Vendor
from apparelrow.apparel.utils import get_pagination_page, select_from_multi_gender

logger = logging.getLogger('apparel.debug')

BROWSE_PAGE_SIZE = 30

DEFAULT_SORT_ARGUMENTS = {
    'pop': 'popularity desc, created desc',
    'lat': 'created desc, popularity desc',
    'exp': 'price desc, popularity desc, created desc',
    'che': 'price asc, popularity desc, created desc'
}

def _to_int(s):
    try:
        return int(s)
    except ValueError:
        return None

def generate_gender_field(params):
    """
    Generate a SOLR expression for the gender field based on params.
    """
    gender_field = 'gender:(W OR M OR U)'
    if 'gender' in params:
        if params['gender'] == 'M' or params['gender'] == 'W':
            gender_field = 'gender:(%s OR U)' % (params['gender'],)

    return gender_field

def set_query_arguments(query_arguments, request, facet_fields=None, currency=None):
    """
    Set query arguments that are common for every browse page access.
    """
    query_arguments['fl'] = 'template:{0}_template'.format(translation.get_language())

    query_arguments['facet'] = 'on'
    query_arguments['facet.limit'] = -1
    query_arguments['facet.mincount'] = 1
    query_arguments['facet.field'] = []

    for field in ['category', 'manufacturer', 'color', 'store']:
        if facet_fields and field in facet_fields:
            query_arguments['facet.field'].append('{!ex=%s}%s' % (field, field))

    if 'fq' not in query_arguments:
        query_arguments['fq'] = []

    query_arguments['fq'].append('published:true')
    query_arguments['fq'].append('django_ct:apparel.product')

    # Category
    if 'category' in request.GET:
       query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('category', 'category', ' OR '.join([x for x in request.GET['category'].split(',')])))

    # Price
    if 'price' in request.GET:
        price = request.GET['price'].split(',')
        if len(price) == 2:
            try:
                min_price = decimal.Decimal(price[0])
                max_price = decimal.Decimal(price[1])
            except decimal.InvalidOperation:
                min_price = max_price = decimal.Decimal('0.00')

            min_price.quantize(decimal.Decimal('1.00'), rounding=decimal.ROUND_HALF_UP)
            max_price.quantize(decimal.Decimal('1.00'), rounding=decimal.ROUND_HALF_UP)
            # Set a large price that we should never encounter
            if max_price >= decimal.Decimal('10000'):
                max_price = decimal.Decimal('1000000000.00')

            if currency:
                query_arguments['fq'].append('{{!tag={0}}}{0}:[{2},{1} TO {3},{1}]'.format('price', currency, str(min_price), str(max_price)))
            else:
                query_arguments['fq'].append('{{!tag={0}}}{0}:[{1} TO {2}]'.format('price', str(min_price), str(max_price)))

    # Only discount
    if 'discount' in request.GET:
        query_arguments['fq'].append('{!tag=%s}discount:true' % ('price',))

    # Brand
    if 'manufacturer' in request.GET:
        query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('manufacturer', 'manufacturer_id', ' OR '.join([x for x in request.GET['manufacturer'].split(',')])))

    # Store
    if 'store' in request.GET:
        query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('store', 'store_id', ' OR '.join([x for x in request.GET['store'].split(',')])))

    # Color and pattern
    color_pattern_list = request.GET.get('color', '').split(',')
    color_pattern_list.extend(request.GET.get('pattern', '').split(','))
    color_pattern_list = [x for x in color_pattern_list if x]
    if color_pattern_list:
       query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('color', 'color', ' OR '.join(color_pattern_list)))

    return query_arguments

def calculate_price_range(request, language):
    pricerange = {'min': 0, 'max': 10000}
    if language in settings.MAX_MIN_CURRENCY:
        pricerange['max'] = settings.MAX_MIN_CURRENCY.get(language)
    pricerange['selected'] = request.GET['price'] if 'price' in request.GET else '%s,%s' % (pricerange['min'], pricerange['max'])

    price = request.GET.get('price', '').split(',')
    if len(price) == 2:
        pricerange['selected_min'] = price[0]
        pricerange['selected_max'] = price[1]
    else:
        pricerange['selected_min'] = pricerange['min']
        pricerange['selected_max'] = pricerange['max']
    return pricerange

def calculate_stores(stores_list):
    stores = []
    for i, value in enumerate(stores_list):
        if i % 2 == 0:
            split = value.split('|')
            stores.append((int(split[1]), split[0]))
    return stores

def calculate_category(categories_list):
    category_ids = map(int, categories_list[::2])
    category_values = map(int, categories_list[1::2])
    categories = dict(zip(category_ids, category_values))
    return categories

def update_query_view(request, view, is_authenticated, query_arguments, gender, result, user_id, user_gender, is_brand):
    if view == 'friends' or 'f' in request.GET:
        user_ids = []
        if is_authenticated:
            user_ids = get_model('profile', 'Follow').objects.filter(user=request.user).values_list('user_follow_id', flat=True)
        else:
            result.update(extra_html=loader.render_to_string('apparel/fragments/browse_follow_user.html', {}, context_instance=RequestContext(request)))
        user_ids_or = ' OR '.join(str(x) for x in (list(user_ids) + [0]))
        query_arguments['fq'].append('user_likes:(%s)' % (user_ids_or,))
        query_arguments['fq'].append('gender:(U OR %s)' % (gender,))
    elif view == 'brands':
        brand_ids = []
        if is_authenticated:
            brand_ids = get_model('apparel', 'Brand').objects.filter(user__followers__user=request.user, user__followers__active=True).values_list('id', flat=True)
        else:
            result.update(extra_html=loader.render_to_string('apparel/fragments/browse_follow_brand.html', {}, context_instance=RequestContext(request)))
        brand_ids_or = ' OR '.join(str(x) for x in (list(brand_ids) + [0]))
        query_arguments['fq'].append('manufacturer_id:(%s)' % (brand_ids_or,))
        query_arguments['fq'].append('gender:(U OR %s)' % (gender,))
    else:
        if user_id:
            if is_brand:
                query_arguments['sort'] = 'availability desc, created desc, popularity desc'
                query_arguments['fq'].append('user_likes:%s OR manufacturer_id:%s' % (user_id, is_brand))
            else:
                query_arguments['sort'] = 'availability desc, %s_uld desc, popularity desc, created desc' % (user_id,)
                query_arguments['fq'].append('user_likes:%s' % (user_id,))
            if user_gender == 'A':
                query_arguments['fq'].append(generate_gender_field(request.GET))
            else:
                query_arguments['fq'].append(generate_gender_field(dict(gender=user_gender)))
        else:
            if view == "latest":
                query_arguments['sort'] = 'availability desc, created desc, popularity desc'
            query_arguments['fq'].append('gender:(U OR %s)' % (gender,))
            query_arguments['fq'].append('market_ss:%s' % request.session.get('location','ALL'))
    return query_arguments, result

def browse_products(request, template='apparel/browse.html', gender=None, user_gender=None, user_id=None, language=None, **kwargs):
    if gender is None and user_gender is None:
        gender = select_from_multi_gender(request, 'shop', None)
        if gender == 'M':
            return HttpResponseRedirect('%s?%s' % (reverse('shop-men'), request.GET.urlencode()))
        else:
            return HttpResponseRedirect('%s?%s' % (reverse('shop-women'), request.GET.urlencode()))
    elif user_gender is None:
        gender = select_from_multi_gender(request, 'shop', gender)

    if not language:
        language = get_language()
    translation.activate(language)

    currency = settings.APPAREL_BASE_CURRENCY
    if language in settings.LANGUAGE_TO_CURRENCY:
        currency = settings.LANGUAGE_TO_CURRENCY.get(language)

    facet_fields = ['category', 'price', 'color', 'manufacturer', 'store']
    query_arguments = {'rows': BROWSE_PAGE_SIZE, 'start': 0}
    query_arguments = set_query_arguments(query_arguments, request, facet_fields, currency=currency)
    disable_availability = kwargs.get('disable_availability', False)
    if not disable_availability:
        query_arguments['fq'].append('availability:true')

    result = {}

    # Sort
    query_arguments['sort'] = DEFAULT_SORT_ARGUMENTS.get(request.GET.get('sort'), DEFAULT_SORT_ARGUMENTS['pop'])

    # Shop views
    view = request.GET.get('view', 'all')
    is_authenticated = request.user.is_authenticated()
    is_brand = None
    if 'is_brand' in kwargs and kwargs['is_brand']:
        is_brand = kwargs['is_brand']
        query_arguments['fq'].append('market_ss:%s' % request.session.get('location','ALL'))
    query_arguments, result = update_query_view(request, view, is_authenticated, query_arguments, gender, result, user_id, user_gender, is_brand)

    # Query string
    query_string = request.GET.get('q')
    if not query_string:
        query_string = '*:*'
    else:
        # If we have a query string use edismax search type and search in
        # specified fields
        query_arguments['qf'] = PRODUCT_SEARCH_FIELDS
        query_arguments['defType'] = 'edismax'

        sort_get = request.GET.get('sort')
        if not sort_get or sort_get == '':
            query_arguments['sort'] = 'score desc'

    query_arguments['f.manufacturer.facet.limit'] = 40
    query_arguments['f.manufacturer.facet.sort'] = 'index'

    brand_search = request.GET.get('brand_search', None)
    if brand_search:
        query_arguments['f.manufacturer.facet.prefix'] = brand_search.lower()

    brand_search_page = int(request.GET.get('brand_search_page', 0))
    if brand_search_page:
        query_arguments['f.manufacturer.facet.offset'] = brand_search_page * query_arguments['f.manufacturer.facet.limit']

    search = ApparelSearch(query_string, **query_arguments)

    facet = search.get_facet()['facet_fields']

    # Calculate manufacturer
    manufacturers = []
    for i, value in enumerate(facet['manufacturer']):
        if i % 2 == 0:
            split = value.split('|')
            manufacturers.append((int(split[-1]), split[-2]))

    if brand_search or brand_search_page:
        return HttpResponse(json.dumps({'manufacturers': manufacturers}), mimetype='application/json')

    # Calculate price range
    pricerange = calculate_price_range(request, language)

    # Calculate store
    stores = calculate_stores(facet['store'])

    # Calculate colors
    colors = [int(value) for i, value in enumerate(facet['color']) if i % 2 == 0]

    # Calculate category
    categories = calculate_category(facet['category'])

    # Calculate paginator
    paged_result, pagination = get_pagination_page(search, BROWSE_PAGE_SIZE,
            request.GET.get('page', 1))

    result.update(pagination=pagination,
                  pricerange=pricerange,
                  manufacturers=manufacturers,
                  stores=stores,
                  colors=colors,
                  categories=categories)

    selected_discount = bool(request.GET.get('discount', None))
    if selected_discount:
        browse_text = ungettext('%(count)s product on sale',
                                '%(count)s products on sale',
                                paged_result.paginator.count) % {
                                    'count': paged_result.paginator.count
                                }
    else:
        browse_text = ungettext('%(count)s product',
                                '%(count)s products',
                                paged_result.paginator.count) % {
                                    'count': paged_result.paginator.count
                                }

    if request.GET.get('q', None):
        browse_text = '%s \'%s\', %s' % (_('Search result for'), request.GET.get('q'), browse_text)

    result.update(browse_text=browse_text)

    paged_result.html = [o.template for o in paged_result.object_list if o and hasattr(o, 'template')]
    paged_result.object_list = []

    if not paged_result.html:
        result.update(extra_html=loader.render_to_string('apparel/fragments/shop_empty.html', {}, context_instance=RequestContext(request)))

    # Update selected
    selected_colors = request.GET.get('color', None)
    if selected_colors:
        try:
            selected_colors = map(int, selected_colors.split(','))
        except ValueError:
            selected_colors = ''
            logger.warning("Trying to access with wrong URL parameters for Embed Shop")
    selected_patterns = request.GET.get('pattern', None)
    if selected_patterns:
        selected_patterns = map(int, selected_patterns.split(','))

    selected_price = request.GET.get('price', None)
    if selected_price:
        selected_price = selected_price.split(',', 1)
        try:
            selected_price = map(int, selected_price)
        except ValueError:
            selected_price = [0,0]

    selected_brands = filter(None, map(_to_int, request.GET.get('manufacturer', '').split(',')))
    selected_brands_data = {}
    for brand in Brand.objects.values('id', 'name').filter(pk__in=selected_brands):
        brand['href'] = '%s?manufacturer=%s' % (reverse('apparelrow.apparel.browse.browse_products'), brand['id'])
        selected_brands_data[brand['id']] = brand

    selected_stores = filter(None, map(_to_int, request.GET.get('store', '').split(',')))
    selected_stores_data = {}
    for store in Vendor.objects.values('id', 'name').filter(pk__in=selected_stores):
        store['href'] = '%s?store=%s' % (reverse('apparelrow.apparel.browse.browse_products'), store['id'])
        selected_stores_data[store['id']] = store

    result.update(
        selected_categories  = filter(None, map(_to_int, request.GET.get('category', '').split(','))),
        selected_colors      = selected_colors,
        selected_patterns    = selected_patterns,
        selected_brands      = selected_brands,
        selected_brands_data = selected_brands_data,
        selected_stores      = selected_stores,
        selected_stores_data = selected_stores_data,
        selected_price       = selected_price,
        selected_gender      = request.GET.get('gender', None),
        selected_discount    = selected_discount,
        selected_sort        = request.GET.get('sort', None),
        selected_view        = request.GET.get('view', None),
        gender               = gender,
    )

    # Serve ajax request
    if request.is_ajax():
        result.update(get_pagination_as_dict(paged_result))
        result.update(
            html = loader.render_to_string('apparel/fragments/product_list.html',
                {
                    'current_page': paged_result,
                    'pagination': pagination
                },
                context_instance=RequestContext(request)
            ),
        )
        return HttpResponse(json.dumps(result), mimetype='application/json')

    # Default colors
    default_colors = Option.objects.filter(option_type__name='color').exclude(value__exact='').all()

    # Default patterns
    default_patterns = Option.objects.filter(option_type__name='pattern').exclude(value__exact='').all()

    # User id
    if user_id:
        result.update(user_gender=user_gender)
        result.update(user_id=user_id)
        result.update(show_filters=True)
        result.update(show_product_brand=True)

    # Serve non ajax request
    result.update(
        default_patterns = default_patterns,
        default_colors = default_colors,
        categories_all = Category.objects.all(),
        current_page = paged_result,
    )

    # Added remaining kwargs for rendering
    result.update(kwargs)

    response = render_to_response(template, result, context_instance=RequestContext(request))

    translation.deactivate()

    return response

def get_pagination_as_dict(paged_result):
    # FIXME: This exists because the JSON exporter is unable to serialise
    # Page and Pagination objects. Perhaps this code could be moved to the
    # exporter module instead?
    try:
        previous_page_number = paged_result.previous_page_number()
    except EmptyPage:
        previous_page_number = None

    try:
        next_page_number = paged_result.next_page_number()
    except EmptyPage:
        next_page_number = None

    return {
        'previous_page_number': previous_page_number,
        'next_page_number': next_page_number,
        'number': paged_result.number,
        'paginator': {
            'num_pages': paged_result.paginator.num_pages,
            'count': paged_result.paginator.count,
        },
    }


def shop_embed(request, user_id, language, gender):
    response = browse_products(request,
                               template='apparel/shop_embed.html',
                               user_gender=gender,
                               language=language,
                               user_id=user_id)

    # Do not update cache key for requests involving a GET parameter
    if not request.GET:
        nginx_key = reverse('shop-embed', args=[user_id, language, gender])
        get_cache('nginx').set(nginx_key, response.content, 60*60*24*20)

    return response


@login_required
def shop_widget(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed("Only POST requests allowed")

    content = {}
    content['language'] = request.POST.get('language', 'sv')
    content['gender'] = request.POST.get('gender', 'A')
    content['width'] = request.POST.get('width', '100')
    content['width_type'] = request.POST.get('width_type', '%')
    content['height'] = request.POST.get('height', '600')
    if content['width_type'] == '%' and int(content['width']) > 100:
        content['width'] = '100'

    return render(request, 'apparel/fragments/shop_widget.html', content)

