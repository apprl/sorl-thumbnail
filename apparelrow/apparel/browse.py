import re
import math
import os.path

from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render_to_response
from django.db.models import Max
from django.db.models import Min
from django.template import RequestContext
from django.template import loader
from django.core.paginator import Paginator
from django.core.paginator import InvalidPage
from django.core.paginator import EmptyPage
from django.core.urlresolvers import reverse
from django.utils.translation import get_language, ugettext_lazy as _

from hanssonlarsson.django.exporter import json

from actstream.models import Follow

from apparel.search import PRODUCT_SEARCH_FIELDS
from apparel.search import ApparelSearch
from apparel.models import Product
from apparel.models import Manufacturer
from apparel.models import Option
from apparel.models import Category
from apparel.decorators import get_current_user
from apparel.utils import get_pagination_page

#FIXME: ugly solution to avoid using get_template_source which is deprecated. Solve this in js and not by using pagination_js template.
PAGINATION_JS_TEMPLATE_SOURCE = open(os.path.join(settings.TEMPLATE_DIRS[0], 'apparel/fragments/pagination_js.html')).read()

BROWSE_PAGE_SIZE = 60

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

def set_query_arguments(query_arguments, request, facet_fields=None, gender=None):
    """
    Set query arguments that are common for every browse page access.
    """
    query_arguments['fl'] = 'template'
    #query_arguments['stats'] = 'on'
    #query_arguments['stats.field'] = 'price'
    query_arguments['facet.range'] = 'price'
    query_arguments['facet.range.start'] = 0
    query_arguments['facet.range.end'] = 11000
    query_arguments['facet.range.gap'] = 10

    query_arguments['facet'] = 'on'
    query_arguments['facet.limit'] = -1
    query_arguments['facet.mincount'] = 1
    query_arguments['facet.field'] = []

    for field in ['category', 'price', 'manufacturer_data', 'color']:
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
                max_price = int(price[1])
                min_price = int(price[0])
            except ValueError:
                max_price = min_price = 0

            if max_price >= 10000:
                query_arguments['fq'].append('{!tag=%s}%s:[%s TO *]' % ('price', 'price', min_price))
            else:
                query_arguments['fq'].append('{!tag=%s}%s:[%s TO %s]' % ('price', 'price', min_price, max_price))

    # Only discount
    if 'discount' in request.GET:
        query_arguments['fq'].append('{!tag=%s}discount:true' % ('price',))

    # Manufacturer
    if 'manufacturer' in request.GET:
        query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('manufacturer_data', 'manufacturer_id', ' OR '.join([x for x in request.GET['manufacturer'].split(',')])))

    # Color and pattern
    color_pattern_list = request.GET.get('color', '').split(',')
    color_pattern_list.extend(request.GET.get('pattern', '').split(','))
    color_pattern_list = [x for x in color_pattern_list if x]
    if color_pattern_list:
       query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('color', 'color', ' OR '.join(color_pattern_list)))

    # Extra
    if 'f' in request.GET and request.user:
        user_ids = list(Follow.objects.filter(user=request.user).values_list('object_id', flat=True)) + [0]
        user_ids_or = ' OR '.join(str(x) for x in user_ids)
        query_arguments['fq'].append('user_likes:({0})'.format(user_ids_or))
        query_arguments['fq'].append('availability:true')
        query_arguments['fq'].append(generate_gender_field(request.GET))
    else:
        query_arguments['fq'].append('availability:true')
        query_arguments['fq'].append('gender:(U OR %s)' % (gender,))

    return query_arguments

def browse_products(request, template='apparel/browse.html', gender=None):
    facet_fields = ['category', 'price', 'color', 'manufacturer_data']
    query_arguments = {'rows': BROWSE_PAGE_SIZE, 'start': 0}
    query_arguments = set_query_arguments(query_arguments, request, facet_fields, gender=gender)

    # Query string
    query_string = request.GET.get('q')
    if not query_string:
        if 'sort' not in query_arguments:
            query_arguments['sort'] = DEFAULT_SORT_ARGUMENTS.get(request.GET.get('sort'), DEFAULT_SORT_ARGUMENTS['pop'])
        query_string = '*:*'

    if query_string != '*:*':
        query_arguments['qf'] = PRODUCT_SEARCH_FIELDS
        query_arguments['defType'] = 'edismax'

    search = ApparelSearch(query_string, **query_arguments)

    facet = search.get_facet()['facet_fields']

    # Calculate price range
    pricerange = {}
    prices = [int(value) for i, value in enumerate(facet['price']) if i % 2 == 0]
    if prices:
        pricerange['max'] = max(prices)
        if pricerange['max'] > 10000:
            pricerange['max'] = 10000
        pricerange['min'] = min(prices)
    else:
        pricerange = {'min': 0, 'max': 0}

    #stats = search.get_stats()['stats_fields']
    #pricerange = {'min': 0, 'max': 0}
    #if 'price' in stats:
        #pricerange['min'] = int(stats['price']['min'])
        #pricerange['max'] = int(stats['price']['max'])
        #if pricerange['max'] > 10000:
            #pricerange['max'] = 10000

    pricerange['selected'] = request.GET['price'] if 'price' in request.GET else '%s,%s' % (pricerange['min'], pricerange['max'])

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

    # Calculate next page
    try:
        next_page = paged_result.paginator.page(paged_result.next_page_number())
    except (EmptyPage, InvalidPage):
        next_page = None

    pages = (paged_result, next_page)

    result = {}
    result.update(pagination=pagination,
                  pricerange=pricerange,
                  manufacturers=manufacturers,
                  colors=colors,
                  categories=categories)

    paged_result.html = [o.template for o in paged_result.object_list if o]
    paged_result.object_list = []

    if next_page is not None:
        next_page.html = [o.template for o in next_page.object_list if o]
        next_page.object_list = []

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
            map(int, selected_price)
        except ValueError:
            selected_price = [0,0]

    selected_brands = filter(None, map(_to_int, request.GET.get('manufacturer', '').split(',')))
    selected_brands_data = {}
    for brand in Manufacturer.objects.values('id', 'name').filter(pk__in=selected_brands):
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
    )

    if request.GET.get('q', None):
        result.update(help_text=_('Showing') + ' \'' + request.GET.get('q') + '\'')
    if request.GET.get('f', None):
        result.update(help_text=_('Showing popular products in your network'))
        if Follow.objects.filter(user=request.user).count() == 0:
            result.update(follow_html=loader.render_to_string('apparel/fragments/browse_follow_user.html', {}, context_instance=RequestContext(request)))

    # Serve ajax request
    if request.is_ajax():
        result.update(get_pagination_as_dict(paged_result))
        result.update(
            html = loader.render_to_string('apparel/fragments/product_list.html',
                {
                    'current_page': paged_result,
                    'pages': pages,
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
        pages = pages,
        templates = {
            'pagination': PAGINATION_JS_TEMPLATE_SOURCE
        },
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
