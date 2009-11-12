from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
from django.utils.translation import ugettext
from apparel.models import *
from django.db.models import Q, Max, Min
from django.template.loader import find_template_source
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from apparel.json import encode

import re
import math
# Create your views here.
from pprint import pprint


WIDE_LIMIT = 10 # FIME: Move to application settings fileI

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
    
    paginator = Paginator(result, 10) #FIXME: Make results per page configurable

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        paged_result = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paged_result = paginator.page(paginator.num_pages)

    #FIXME: We don't return the paged result because it's not JSON serializable
    return HttpResponse(
        encode(paged_result.object_list),
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

    return HttpResponse(
        encode(result),
        mimetype='text/json'
    )
    
def filter(request):
    pricerange = VendorProduct.objects.aggregate(min=Min('price'), max=Max('price'))
    pricerange['min'] = int(100 * math.floor(float(pricerange['min']) / 100))
    pricerange['max'] = int(100 * math.ceil(float(pricerange['max']) / 100))
    #FIXME: Create a generic way of getting relevant templates and putting them into the context
    template_source, template_origin = find_template_source('apparel/fragments/product_small.html')
    products = Product.objects.all()
    paginator = Paginator(products, 10) #FIXME: Make number per page configurable
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        paged_products = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paged_products = paginator.page(paginator.num_pages)
    result = {
        'categories': Category._tree_manager.all(),
        'manufacturers': Manufacturer.objects.all(),
        'genders': Option.objects.filter(option_type__name__iexact='gender'),
        'colors': Option.objects.filter(option_type__name__iexact='color'),
        'pricerange': pricerange,
        'products': paged_products,
        'product_template': template_source,
    }
    return render_to_response('filter.html', result)

def looks():
    pass

def looks():
    pass

def looks():
    pass


