import re
import math

from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render_to_response
from django.db.models import Max
from django.db.models import Min
from django.template import RequestContext
from django.template import Template
from django.template import loader
from django.template.loader import get_template
from django.template.loader import find_template_source
from django.core.paginator import Paginator
from django.core.paginator import InvalidPage
from django.core.paginator import EmptyPage

from hanssonlarsson.django.exporter import json

from pysolr import Solr

from haystack.forms import FacetedSearchForm
from haystack.query import EmptySearchQuerySet
from haystack.query import SearchQuerySet

from apparel.models import Product
from apparel.models import Manufacturer
from apparel.models import Option
from apparel.models import Category

BROWSE_PAGE_SIZE = 12
BROWSE_PAGE_MAX  = 100

FACET_FILTER_OPTIONS = ['category', 'price', 'manufacturer', 'color']

def _to_int(s):
    try:
        return int(s)
    except ValueError:
        return None

def filter_query(query, params):
    for field in FACET_FILTER_OPTIONS:
        if field == 'category':
            query = query.facet('{!ex=category}%s' % (field,))
        else:
            query = query.facet('%s' % (field,))

        if field in params:
            if field == 'price':
                price = params[field].split(',')
                query = query.narrow('%s:[%s TO %s]' % (field + '_exact', query.query.clean(price[0]), query.query.clean(price[1])))
            elif field == 'category':
                query = query.narrow('{!tag=category}%s:(%s)' % (field + '_exact', ' OR '.join([query.query.clean(x) for x in params[field].split(',')])))
            else:
                query = query.narrow('%s:(%s)' % (field + '_exact', ' OR '.join([query.query.clean(x) for x in params[field].split(',')])))

    if 'gender' in params and len(params.get('gender')) == 1:
        query = query.narrow('gender:%s' % (query.query.clean(params.get('gender')),))
    else:
        query = query.narrow('gender:(W OR M OR U)')

    if 'q' in params:
        query = query.filter(content=query.query.clean(params.get('q', '')))

    return query

def browse_products(request):
    query = ''
    results = EmptySearchQuerySet()

    sqs = SearchQuerySet().models(Product)
    sqs = filter_query(sqs, request.GET)
    sqs = sqs.load_all()

    facet = sqs.facet_counts()

    # Calculate price range. Using Solr directly because haystack have no
    # support for stats component.
    solr = Solr(settings.HAYSTACK_SOLR_URL)
    price_result = solr.search(q=sqs.query.build_query(), fq=list(sqs.query.narrow_queries), **{'stats': 'on', 'stats.field': 'price'})
    if price_result:
        pricerange = {
            'max': int(round(price_result.stats['stats_fields']['price']['max'] + 50, -2)),
            'min': int(round(price_result.stats['stats_fields']['price']['min'] - 50, -2)),
        }
        if pricerange['min'] < 0:
            pricerange['min'] = 0
    else:
        pricerange = {'max': 0, 'min': 0}
    pricerange['selected'] = request.GET['price'] if 'price' in request.GET else '%s,%s' % (pricerange['min'], pricerange['max'])

    # Calculate manufacturer
    manufacturers = Manufacturer.objects.filter(pk__in=[x[0] for x in facet['fields']['manufacturer'] if x[1] > 0])

    # Calculate colors
    if request.is_ajax():
        colors = [_to_int(x[0]) for x in facet['fields']['color'] if x[1] > 0]
    else:
        #colors = Option.objects.filter(option_type__name='color').all()
        colors = Option.objects.filter(option_type__name='color').filter(pk__in=[_to_int(x[0]) for x in facet['fields']['color']])

    # Calculate category
    categories = [_to_int(x[0]) for x in facet['fields']['category'] if x[1] > 0]

    # Calculate paginator
    paginator = Paginator(sqs, BROWSE_PAGE_SIZE)
    try:
        paged_result = paginator.page(int(request.GET.get('page', 1)))
    except (EmptyPage, InvalidPage):
        paged_result = paginator.page(paginator.num_pages)
    except ValueError:
        paged_result = paginator.page(1)

    # Calculate next page
    try:
        next_page = paged_result.paginator.page(paged_result.next_page_number())
    except (EmptyPage, InvalidPage):
        next_page = None

    pages = (paged_result, next_page)

    left, mid, right = get_pagination(paged_result.paginator, paged_result.number)
    pagination = {
        'left': left,
        'mid': mid,
        'right': right
    }

    result = {}
    result.update(pagination=pagination,
                  pricerange=pricerange,
                  manufacturers=manufacturers,
                  colors=colors,
                  categories=categories)

    paged_result.html = [o.template for o in paged_result.object_list]
    paged_result.object_list = []

    if next_page is not None:
        next_page.html = [o.template for o in next_page.object_list]
        next_page.object_list = []

    # Update selected
    selected_colors = request.GET.get('color', None)
    if selected_colors:
        selected_colors = selected_colors.split(',')

    selected_price = request.GET.get('price', None)
    if selected_price:
        selected_price = selected_price.split(',', 1)

    result.update(
        selected_categories = filter(None, map(_to_int, request.GET.get('category', '').split(','))),
        selected_colors     = selected_colors,
        selected_brands     = filter(None, map(_to_int, request.GET.get('manufacturer', '').split(','))),
        selected_price      = selected_price,
        selected_gender     = request.GET.get('gender', None),
    )

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
        return HttpResponse(
            json.encode(result),
            mimetype='text/json'
        )

    # Serve non ajax request
    result.update(
        categories_all=Category._tree_manager.all(),
        current_page = paged_result,
        pages = pages,
        templates = {
            'pagination': get_template_source('apparel/fragments/pagination_js.html')
        },
    )

    return render_to_response('apparel/browse.html', result, context_instance=RequestContext(request))

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

def browse_manufacturers(request, **kwargs):
    """
    Browse manufacturers view.
    """
    sqs = SearchQuerySet().models(Manufacturer)

    page = request.GET.get('mpage', 1)
    term = request.GET.get('mname', None)
    if term:
        sqs = sqs.filter(auto=term)

    mp = Paginator(sqs.order_by('name').load_all(), settings.APPAREL_MANUFACTURERS_PAGE_SIZE)
    try:
        manufacturers = [x.object for x in mp.page(page).object_list if x]
    except EmptyPage:
        manufacturers = []
    except InvalidPage:
        manufacturers = [x.object for x in mp.page(1).object_list if x]

    return HttpResponse(json.encode(manufacturers), mimetype='application/json')

def get_template_source(template):
    template_source, template_origin = find_template_source(template)
    return template_source

def get_pagination(paginator, page_num, on_ends=2, on_each_side=3):
    """
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
        return None, paginator.page_range, None

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

    return left, mid, right

def js_template(str, request=None, context=None):
    if context is None:
        context = RequestContext(request)

    str = str.replace('{{', '${').replace('}}', '}')
    str = re.sub(r'\{%\s*include "(.+?)"\s*%\}', lambda m: js_template(get_template_source(m.group(1)), context=context), str)

    return Template(str).render(context)
