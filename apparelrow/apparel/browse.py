import re
import math
import os.path
import decimal

from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render_to_response
from django.db.models import Max
from django.db.models import Min
from django.db.models.loading import get_model
from django.template import RequestContext
from django.template import loader
from django.core.paginator import Paginator
from django.core.paginator import InvalidPage
from django.core.paginator import EmptyPage
from django.core.urlresolvers import reverse
from django.utils.translation import get_language, ugettext_lazy as _

from hanssonlarsson.django.exporter import json

from apparel.search import PRODUCT_SEARCH_FIELDS
from apparel.search import ApparelSearch
from apparel.models import Product
from apparel.models import Brand
from apparel.models import Option
from apparel.models import Category
from apparel.utils import get_pagination_page

from profile.models import Follow

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

def set_query_arguments(query_arguments, request, facet_fields=None, gender=None, currency=None):
    """
    Set query arguments that are common for every browse page access.
    """
    query_arguments['fl'] = 'template'

    query_arguments['facet'] = 'on'
    query_arguments['facet.limit'] = -1
    query_arguments['facet.mincount'] = 1
    query_arguments['facet.field'] = []

    for field in ['category', 'manufacturer_data', 'color']:
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
        query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('manufacturer_data', 'manufacturer_id', ' OR '.join([x for x in request.GET['manufacturer'].split(',')])))

    # Color and pattern
    color_pattern_list = request.GET.get('color', '').split(',')
    color_pattern_list.extend(request.GET.get('pattern', '').split(','))
    color_pattern_list = [x for x in color_pattern_list if x]
    if color_pattern_list:
       query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('color', 'color', ' OR '.join(color_pattern_list)))

    return query_arguments

def browse_products(request, template='apparel/browse.html', gender=None):
    language = get_language()
    currency = settings.APPAREL_BASE_CURRENCY
    if language in settings.LANGUAGE_TO_CURRENCY:
        currency = settings.LANGUAGE_TO_CURRENCY.get(language)

    facet_fields = ['category', 'price', 'color', 'manufacturer_data']
    query_arguments = {'rows': BROWSE_PAGE_SIZE, 'start': 0}
    query_arguments = set_query_arguments(query_arguments, request, facet_fields, gender=gender, currency=currency)

    # Follower products
    user_ids = []
    if 'f' in request.GET and request.user:
        user_ids = list(Follow.objects.filter(user=request.user.get_profile()).values_list('user_follow__user_id', flat=True))
        for x in (user_ids + [0]):
            print x
        user_ids_or = ' OR '.join(str(x) for x in (user_ids + [0]))
        query_arguments['fq'].append('user_likes:({0})'.format(user_ids_or))
        query_arguments['fq'].append('availability:true')
        query_arguments['fq'].append(generate_gender_field(request.GET))
    else:
        query_arguments['fq'].append('availability:true')
        query_arguments['fq'].append('gender:(U OR %s)' % (gender,))

    # Sort
    query_arguments['sort'] = DEFAULT_SORT_ARGUMENTS.get(request.GET.get('sort'), DEFAULT_SORT_ARGUMENTS['pop'])

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

    search = ApparelSearch(query_string, **query_arguments)

    facet = search.get_facet()['facet_fields']

    # Calculate price range
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

    # Calculate manufacturer
    manufacturers = []
    for i, value in enumerate(facet['manufacturer_data']):
        if i % 2 == 0:
            split = value.rsplit('|', 1)
            manufacturers.append((int(split[1]), split[0]))

    # Calculate colors
    colors = [int(value) for i, value in enumerate(facet['color']) if i % 2 == 0]

    # Calculate category
    category_ids = map(int, facet['category'][::2])
    category_values = map(int, facet['category'][1::2])
    categories = dict(zip(category_ids, category_values))

    # Calculate paginator
    paged_result, pagination = get_pagination_page(search, BROWSE_PAGE_SIZE,
            request.GET.get('page', 1))

    result = {}
    result.update(pagination=pagination,
                  pricerange=pricerange,
                  manufacturers=manufacturers,
                  colors=colors,
                  categories=categories)

    if request.GET.get('q', None):
        result.update(help_text=_('Showing') + ' \'' + request.GET.get('q') + '\'')
    if request.GET.get('f', None):
        result.update(help_text=_('Showing your friends\' favorites'))
        if not user_ids:
            result.update(follow_html=loader.render_to_string('apparel/fragments/browse_follow_user.html', {}, context_instance=RequestContext(request)))

    paged_result.html = [o.template for o in paged_result.object_list if o]
    paged_result.object_list = []

    # Update selected
    selected_colors = request.GET.get('color', None)
    if selected_colors:
        selected_colors = selected_colors.split(',')

    selected_patterns = request.GET.get('pattern', None)
    if selected_patterns:
        selected_patterns = selected_patterns.split(',')

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
        brand['href'] = '%s?manufacturer=%s' % (reverse('apparel.browse.browse_products'), brand['id'])
        selected_brands_data[brand['id']] = brand

    result.update(
        selected_categories  = filter(None, map(_to_int, request.GET.get('category', '').split(','))),
        selected_colors      = selected_colors,
        selected_patterns    = selected_patterns,
        selected_brands      = selected_brands,
        selected_brands_data = selected_brands_data,
        selected_price       = selected_price,
        selected_gender      = request.GET.get('gender', None),
        selected_discount    = bool(request.GET.get('discount', None)),
        selected_sort        = request.GET.get('sort', None),
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
        return HttpResponse(json.encode(result), mimetype='text/json')

    # Default colors
    default_colors = Option.objects.filter(option_type__name='color').exclude(value__exact='').all()

    # Default patterns
    default_patterns = Option.objects.filter(option_type__name='pattern').exclude(value__exact='').all()

    # Serve non ajax request
    result.update(
        default_patterns = default_patterns,
        default_colors = default_colors,
        categories_all = Category.objects.all(),
        current_page = paged_result,
    )

    # Set APPAREL_GENDER
    result.update(APPAREL_GENDER=gender)

    response = render_to_response(template, result, context_instance=RequestContext(request))
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)
    return response

def get_pagination_as_dict(paged_result):
    # FIXME: This exists because the JSON exporter is unable to serialise
    # Page and Pagination objects. Perhaps this code could be moved to the
    # exporter module instead?
    return {
        'previous_page_number': paged_result.previous_page_number(),
        'next_page_number': paged_result.next_page_number(),
        'number': paged_result.number,
        'paginator': {
            'num_pages': paged_result.paginator.num_pages,
            'count': paged_result.paginator.count,
        },
    }
