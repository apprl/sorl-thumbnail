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

from apparelrow.search import ApparelSearch
from apparel.models import Product
from apparel.models import Manufacturer
from apparel.models import Option
from apparel.models import Category
from apparel.decorators import get_current_user
from apparel.utils import get_pagination

#FIXME: ugly solution to avoid using get_template_source which is deprecated. Solve this in js and not by using pagination_js template.
PAGINATION_JS_TEMPLATE_SOURCE = open(os.path.join(settings.TEMPLATE_DIRS[0], 'apparel/fragments/pagination_js.html')).read()

BROWSE_PAGE_SIZE = 60

def _to_int(s):
    try:
        return int(s)
    except ValueError:
        return None

def set_query_arguments(query_arguments, params, current_user=None, facet_fields=None, profile=None):
    """
    Set query arguments that are common for every browse page access.
    """
    query_arguments['facet'] = 'on'
    query_arguments['facet.limit'] = -1
    query_arguments['facet.mincount'] = 1
    query_arguments['facet.field'] = []

    query_arguments['qf'] = 'manufacturer_name category_names^40 product_name color_names^40 description'
    query_arguments['defType'] = 'edismax'

    if 'fq' not in query_arguments:
        query_arguments['fq'] = []

    for field in ['category', 'price', 'manufacturer', 'color']:
        if facet_fields and field in facet_fields:
            query_arguments['facet.field'].append('{!ex=%s}%s' % (field, field))

        if field in params:
            tag = '{!tag=%s}%s' % (field, field + '_exact')
            if field == 'price':
                price = params[field].split(',')
                if len(price) == 2:
                    query_arguments['fq'].append('%s:[%s TO %s]' % (tag, price[0], price[1]))
            else:
                query_arguments['fq'].append('%s:(%s)' % (tag, ' OR '.join([x for x in params[field].split(',')])))

    if 'gender' in params:
        if params['gender'] == 'M':
            query_arguments['fq'].append('gender:(M OR U)')
        elif params['gender'] == 'W':
            query_arguments['fq'].append('gender:(W OR U)')
        else:
            query_arguments['fq'].append('gender:(W OR M OR U)')
    else:
        query_arguments['fq'].append('gender:(W OR M OR U)')

    if 'f' in params and current_user:
        user_ids = list(Follow.objects.filter(user=current_user).values_list('object_id', flat=True)) + [0]
        user_ids_or = ' OR '.join(str(x) for x in user_ids)
        query_arguments['fq'].append('user_likes:({0}) OR user_wardrobe:({0})'.format(user_ids_or))
    elif profile:
        query_arguments['fq'].append('user_wardrobe:%s' % (profile.user.id,))
    else:
        query_arguments['fq'].append('availability:true')

    query_arguments['fq'].append('django_ct:apparel.product')

    return query_arguments

def browse_products(request, template='apparel/browse.html', extra_context=None):
    facet_fields = ['category', 'price', 'manufacturer', 'color']
    query_arguments = {'rows': BROWSE_PAGE_SIZE, 'start': 0}
    if extra_context and 'profile' in extra_context:
        # wardrobe
        query_arguments = set_query_arguments(query_arguments, request.GET, request.user, facet_fields, profile=extra_context['profile'])
        query_arguments['sort'] = ['availability desc', 'popularity desc']
    else:
        query_arguments = set_query_arguments(query_arguments, request.GET, request.user, facet_fields)

    query_string = request.GET.get('q')
    if not query_string:
        query_arguments['sort'] = 'popularity desc'
        query_string = '*:*'

    search = ApparelSearch(query_string, **query_arguments)

    facet = search.get_facet()['facet_fields']

    # Calculate price range
    pricerange = {}
    prices = [int(value) for i, value in enumerate(facet['price']) if i % 2 == 0]
    if prices:
        pricerange['max'] = max(prices)
        pricerange['min'] = min(prices)
    else:
        pricerange = {'min': 0, 'max': 0}
    pricerange['selected'] = request.GET['price'] if 'price' in request.GET else '%s,%s' % (pricerange['min'], pricerange['max'])

    # Calculate manufacturer
    manufacturers = Manufacturer.objects.filter(pk__in=[int(value) for i, value in enumerate(facet['manufacturer']) if i % 2 == 0])
    mp = Paginator(manufacturers, settings.APPAREL_MANUFACTURERS_PAGE_SIZE)
    try:
        manufacturers = [x for x in mp.page(1).object_list if x]
    except InvalidPage:
        manufacturers = []

    # Calculate colors
    colors = [int(value) for i, value in enumerate(facet['color']) if i % 2 == 0]


    # Calculate category
    categories = [int(value) for i, value in enumerate(facet['category']) if i % 2 == 0]

    # Calculate paginator
    paginator = Paginator(search, BROWSE_PAGE_SIZE)
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

    paged_result.html = [o.template for o in paged_result.object_list if o]
    paged_result.object_list = []

    if next_page is not None:
        next_page.html = [o.template for o in next_page.object_list if o]
        next_page.object_list = []

    # Update selected
    selected_colors = request.GET.get('color', None)
    if selected_colors:
        selected_colors = selected_colors.split(',')

    selected_price = request.GET.get('price', None)
    if selected_price:
        selected_price = selected_price.split(',', 1)

    selected_brands = filter(None, map(_to_int, request.GET.get('manufacturer', '').split(',')))
    selected_brands_data = {}
    for brand in Manufacturer.objects.values('id', 'name').filter(pk__in=selected_brands):
        brand['href'] = '%s?manufacturer=%s' % (reverse('apparel.browse.browse_products'), brand['id'])
        selected_brands_data[brand['id']] = brand

    result.update(
        selected_categories  = filter(None, map(_to_int, request.GET.get('category', '').split(','))),
        selected_colors      = selected_colors,
        selected_brands      = selected_brands,
        selected_brands_data = selected_brands_data,
        selected_price       = selected_price,
        selected_gender      = request.GET.get('gender', None),
    )

    # Extra context
    if extra_context:
        result.update(extra_context)

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
        return HttpResponse(
            json.encode(result),
            mimetype='text/json'
        )
    else:
        all_colors = Option.objects.filter(option_type__name='color').all()
        result.update(all_colors=all_colors)

    # Serve non ajax request
    result.update(
        categories_all=Category._tree_manager.all(),
        current_page = paged_result,
        pages = pages,
        templates = {
            'pagination': PAGINATION_JS_TEMPLATE_SOURCE
        },
    )

    return render_to_response(template, result, context_instance=RequestContext(request))

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

@get_current_user
def browse_wardrobe(request, profile):
    return browse_products(request,
            template='profile/wardrobe.html',
            extra_context={'profile': profile})

def browse_manufacturers(request, **kwargs):
    """
    Browse manufacturers view.
    """
    page = request.GET.get('mpage', 1)
    term = request.GET.get('mname', None)

    # Initial query arguments for rows and start position
    query_arguments = {'rows': settings.APPAREL_MANUFACTURERS_PAGE_SIZE, 'start': 0}

    # Update query arguments for browse page
    query_arguments = set_query_arguments(query_arguments, request.GET, request.user, ['manufacturer'])

    # Override qf argument
    query_arguments['qf'] = 'manufacturer_auto'

    # Set query string
    query_string = '*:*'
    if term:
        query_string = '%s' % (term,)

    # Do search on query string with query arguments
    search = ApparelSearch(query_string, **query_arguments)

    # Get facet results
    facet = search.get_facet()['facet_fields']

    manufacturers = Manufacturer.objects.values('id', 'name').filter(pk__in=[int(value) for i, value in enumerate(facet['manufacturer']) if i % 2 == 0]).order_by('name')
    mp = Paginator(manufacturers, settings.APPAREL_MANUFACTURERS_PAGE_SIZE)
    try:
        manufacturers = [x for x in mp.page(page).object_list if x]
    except InvalidPage:
        manufacturers = []

    return HttpResponse(json.encode(manufacturers), mimetype='application/json')

