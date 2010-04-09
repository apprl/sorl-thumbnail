import logging
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext
from apparel.models import *
from apparel.forms import *
from django.db.models import Q, Max, Min
from django.template.loader import find_template_source
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from hanssonlarsson.django.exporter import json
from apparel.decorators import seamless_request_handling

from recommender.models import Recommender
from voting.models import Vote

import re
import math
# Create your views here.
from pprint import pprint

BROWSE_PAGE_SIZE = 12
WIDE_LIMIT = 4 # FIME: Move to application settings fileI

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

def search(request, model):
    result = None
    klass  = {
        'products'     : 'Product',
        'manufacturers': 'Manufacturer',
        'categories'   : 'Category',
        'vendors'      : 'Vendor',
    }.get(model)
    
    query, page = get_query_and_page(request)
    if klass:
        klass  = eval(klass)
        result = klass.objects.search(query)
    else:
        raise Exception('No model to search for')
    
    paginator = Paginator(result, BROWSE_PAGE_SIZE)

    try:
        paged_result = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paged_result = paginator.page(paginator.num_pages)

    left, mid, right = get_pagination(paginator, page)

    #FIXME: We don't return the paged result because it's not JSON serializable
    response = {
        'object_list': paged_result.object_list,
        'previous_page_number': paged_result.previous_page_number(),
        'next_page_number': paged_result.next_page_number(),
        'number': paged_result.number,
        'paginator': {
            'num_pages': paged_result.paginator.num_pages,
            'count': paged_result.paginator.count,
        },
        'pagination': {
            'left': left,
            'right': right,
            'mid': mid,
        }    
    }
    return HttpResponse(
        json.encode(response),
        mimetype='text/json'
    )


def wide_search(request):
    query  = request.GET.get('s')
    result = {
        'products': Product.objects.filter(product_name__icontains=query, description__icontains=query)[:WIDE_LIMIT],
        'manufacturers': Manufacturer.objects.filter(name__icontains=query)[:WIDE_LIMIT],
        'categories': Category.objects.filter(name__icontains=query)[:WIDE_LIMIT],
        'vendors': Vendor.objects.filter(name__icontains=query)[:WIDE_LIMIT],
    }
    templates = {
        'products': get_template_source('apparel/fragments/product_small.html'),
    }

    return HttpResponse(
        json.encode(dict(result=result, templates=templates)),
        mimetype='text/json'
    )

def get_pricerange(request):
    pricerange = VendorProduct.objects.aggregate(min=Min('price'), max=Max('price'))
    if pricerange['min'] is None:
        pricerange['min'] = 0
    else:
        pricerange['min'] = int(100 * math.floor(float(pricerange['min']) / 100))
    if pricerange['max'] is None:
        pricerange['max'] = 10000
    else:
        pricerange['max'] = int(100 * math.ceil(float(pricerange['max']) / 100))
    pricerange['selected'] = request.GET['1:vp.price:range'] if '1:vp.price:range' in request.GET else '%s,%s' % (pricerange['min'],pricerange['max'])
    return pricerange

def get_filter(request):
    return {
        'categories': Category._tree_manager.all(),
        'manufacturers': Manufacturer.objects.all(),
        'genders': Option.objects.filter(option_type__name__iexact='gender'),
        'colors': Option.objects.filter(option_type__name__iexact='color'),
        'pricerange': get_pricerange(request),
    }

def index(request):
    ctx = get_filter(request)
    #FIXME: This just selects the top voted objects. We should implement a better popularity algorithm, see #69
    ctx['popular_looks'] = Vote.objects.get_top(Look, limit=8) #Look.objects.all()[:8]
    return render_to_response('index.html', ctx)

def get_query_and_page(request):
    query = request.GET.copy()
    page  = int(query.pop('page', [1])[0]) # all values are lists in the QueryDict object and we never expect more than one

    return query, page

def browse(request):
    query, page = get_query_and_page(request)
    
    if len(query):
        products = Product.objects.search(query)
    else:
        products = Product.objects.all()
    
    paginator = Paginator(products, BROWSE_PAGE_SIZE)
    
    try:
        paged_products = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paged_products = paginator.page(paginator.num_pages)

    left, mid, right = get_pagination(paginator, page)


    result = get_filter(request)
    result['products'] = paged_products
    result['product_count_template'] = js_template(get_template_source('apparel/fragments/product_count.html'))
    result['product_template'] = js_template(get_template_source('apparel/fragments/product_small.html'))
    result['pagination_template'] = get_template_source('apparel/fragments/pagination_js.html')
    result['pagination'] = {
        'left': left,
        'right': right,
        'mid': mid,
    }    
        
    return render_to_response('apparel/browse.html', result)

def js_template(str):
    return str.replace('{%', '<%').replace('%}', '%>').replace('{{', '<%=').replace('}}', '%>')

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    viewed_products = request.session.get('viewed_products', [])
    viewed_products.append(product.id)
    request.session['viewed_products'] = viewed_products
    
    user_looks = Look.objects.filter(user=request.user) if request.user.is_authenticated() else []
    
    return render_to_response(
            'apparel/product_detail.html',
            {
                'look_button_template': js_template(get_template_source('apparel/fragments/look_button.html')),
                'object': product,
                'user_looks': user_looks,
                'looks_with_product': Look.objects.filter(products=product),
                'viewed_products': Product.objects.filter(pk__in=viewed_products),
            })

def save_look_product(request):
    try:
        lp = LookProduct.objects.get(product__id=request.POST['product'], look__id=request.POST['look'])
        form = LookProductForm(request.POST, instance=lp)
    except LookProduct.DoesNotExist:
        form = LookProductForm(request.POST)
    form.save()
    return HttpResponseRedirect(reverse('apparel.views.look_detail', args=(request.POST['look'],)))

def look_detail(request, slug):
    look = get_object_or_404(Look, slug=slug)
    looks_by_user = Look.objects.filter(user=look.user).exclude(pk=look.id)
    similar_looks = [] #Recommender.objects.get_similar_items(look, User.objects.all(), Look.objects.all(), 0)
    return render_to_response('apparel/look_detail.html', dict(object=look, looks_by_user=looks_by_user, similar_looks=similar_looks, tooltips=True))

def look_edit(request, slug):
    look = get_object_or_404(Look, slug=slug)
    if request.method == 'POST':
        form = LookForm(request.POST, request.FILES, instance=look)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(look.get_absolute_url())
    else:
        form = LookForm(instance=look)

    return render_to_response('apparel/look_edit.html', dict(object=look, form=form))

def looks():
    pass

def get_template_source(template):
    template_source, template_origin = find_template_source(template)
    return template_source



@seamless_request_handling
@login_required
def add_to_look(request):
    product = Product.objects.get(pk=request.POST.get('product_id'))
    
    
    if 'look_id' in request.POST:
        look = Look.objects.get(pk=request.POST['look_id'])
        created = False
    else:
        look = Look(user=request.user, title=request.POST.get('new_name'))
        look.save()
        created = True
    
          
    lp, c = LookProduct.objects.get_or_create(product=product, look=look, width=product.product_image.width, height=product.product_image.height)
    if c: lp.save()
    
    return ({'look': look, 'created': created}, HttpResponseRedirect(reverse('apparel.views.look_detail', args=(look.slug,))))

@seamless_request_handling
@login_required
def add_to_wardrobe(request):
    """
    Adds a product to a user's wardrobe (and creates it if necessary)
    """
    
    wardrobe, created = Wardrobe.objects.get_or_create(user=request.user)
    wardrobe.products.add(Product.objects.get(pk=request.POST.get('product_id')))
    wardrobe.save() # FIXME: Only save if created?
    
    return wardrobe
