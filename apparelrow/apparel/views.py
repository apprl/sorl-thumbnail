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

from recommender.models import Recommender

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
    
    if klass:
        klass  = eval(klass)
        result = klass.objects.search(request.GET)
    else:
        raise Exception('No model to search for')
    
    paginator = Paginator(result, BROWSE_PAGE_SIZE)

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

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

def get_filter():
    pricerange = VendorProduct.objects.aggregate(min=Min('price'), max=Max('price'))
    if pricerange['min'] is None:
        pricerange['min'] = 0
    else:
        pricerange['min'] = int(100 * math.floor(float(pricerange['min']) / 100))
    if pricerange['max'] is None:
        pricerange['max'] = 10000
    else:
        pricerange['max'] = int(100 * math.ceil(float(pricerange['max']) / 100))
    return {
        'categories': Category._tree_manager.all(),
        'manufacturers': Manufacturer.objects.all(),
        'genders': Option.objects.filter(option_type__name__iexact='gender'),
        'colors': Option.objects.filter(option_type__name__iexact='color'),
        'pricerange': pricerange
    }

def index(request):
    ctx = get_filter()
    ctx['popular_looks'] = Look.objects.all()[:8]
    return render_to_response('index.html', ctx)

def browse(request):
    query = request.GET.copy()
    page  = int(query.pop('page', [1])[0]) # all values are lists in the QueryDict object and we never expect more than one
    
    if len(query):
        products = Product.objects.search(query)
    else:
        products = Product.objects.all()
    
    #FIXME: Create a generic way of getting relevant templates and putting them into the context
    product_count_template = get_template_source('apparel/fragments/product_count.html')
    product_template = get_template_source('apparel/fragments/product_small.html')
    pagination_template = get_template_source('apparel/fragments/pagination.html')
    paginator = Paginator(products, BROWSE_PAGE_SIZE)
    
    try:
        paged_products = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paged_products = paginator.page(paginator.num_pages)

    left, mid, right = get_pagination(paginator, page)


    result = get_filter()
    result['products'] = paged_products
    result['product_count_template'] = js_template(product_count_template)
    result['product_template'] = js_template(product_template)
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
    return render_to_response(
            'apparel/product_detail.html',
            {
                'object': product,
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

def add_to_look(request):
    product = get_object_or_404(Product, pk=request.POST['product_id'])
    if 'look_id' in request.POST:
        look = get_object_or_404(Look, pk=request.POST['look_id'])
    else:
        look = Look(user=request.user)
        look.save()
    lp = LookProduct(product=product, look=look, width=product.product_image.width, height=product.product_image.height)
    lp.save()
    return HttpResponseRedirect(reverse('apparel.views.look_detail', args=(look.id,)))

def look_detail(request, slug):
    look = get_object_or_404(Look, slug=slug)
    looks_by_user = Look.objects.filter(user=look.user).exclude(pk=look.id)
    similar_looks = Recommender.objects.get_similar_items(look, User.objects.all(), Look.objects.all(), 0)
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

def add_to_wardrobe(request):
    """
    Adds a product to a user's wardrobe (and creates it if necessary)
    """
    
    # FIXME: Support non-ajax requests
    response = {}
    
    if not request.user.is_authenticated():
        response['success'] = False
        response['error_message'] = 'Login required'
        response['login_url'] = '%s?next=%s' % (reverse('django.contrib.auth.views.login'), request.META.get('HTTP_REFERER', '/'))
        
    elif not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    else:
        # Create wardrobe if 
        pk = request.POST.get('product_id')
        w, created = Wardrobe.objects.get_or_create(user=request.user)
        try:
            w.products.add(Product.objects.get(pk=pk))
        except ObjectDoesNotExist, e:
            response['success'] = False
            response['error_message'] = ugettext('The product with id %s does not exist' % pk)
        else:
            # Need to save changes to w?
            response['success'] = True
    
    return HttpResponse(
        json.encode(response),
        mimetype='text/json'
    )

    
