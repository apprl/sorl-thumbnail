import logging, re, math, copy
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext
from django.db.models import Q, Max, Min
from django.template import RequestContext, Template, Context
from django.template.loader import find_template_source
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required

from sorl.thumbnail.main import DjangoThumbnail
from hanssonlarsson.django.exporter import json
from recommender.models import Recommender
from voting.models import Vote

from apparel.decorators import seamless_request_handling
from apparel.manager import QueryParser, InvalidExpression
from apparel.models import *
from apparel.forms import *


BROWSE_PAGE_SIZE = 12
BROWSE_PAGE_MAX  = 100
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
    
    paginator = Paginator(result, BROWSE_PAGE_MAX if page == -1 else BROWSE_PAGE_SIZE)

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
        },
        'criteria_filter': get_criteria_filter(request, result),
    }
    return HttpResponse(
        json.encode(response),
        mimetype='text/json'
    )


def get_criteria_filter(request, result):
    criterion = request.GET.get('criterion')
    if criterion == 'category':
        return {
            'manufacturers': map(lambda o: str(o['id']), Manufacturer.objects.filter(id__in=result.values('manufacturer__id')).values('id')),
            'options': map(lambda o: o['value'], Option.objects.filter(product__id__in=result.values('id')).values('value').distinct()),
        }
    elif criterion == 'manufacturer':
        return {
            'categories': map(lambda o: str(o['id']), Category.objects.filter(id__in=result.values('category__id')).values('id')),
            'options': map(lambda o: o['value'], Option.objects.filter(product__id__in=result.values('id')).values('value').distinct()),
        }
    elif criterion is None:
        return {
            'categories': [],
            'manufacturers': [],
            'options': [],
        }
    
    return {}

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
        'manufacturers': Manufacturer.objects.all().order_by('name'),
        'genders': Option.objects.filter(option_type__name__iexact='gender'),
        'colors': Option.objects.filter(option_type__name__iexact='color'),
        'pricerange': get_pricerange(request),
    }

def index(request):
    ctx = get_filter(request)
    # FIXME: This just selects the top voted objects. We should implement a better popularity algorithm, see #69
    ctx['popular_looks'] = Vote.objects.get_top(Look, limit=8)
    ctx['categories']    = ctx['categories'].filter(on_front_page=True)
    return render_to_response('index.html', ctx, context_instance=RequestContext(request))

def get_query_and_page(request):
    query = request.GET.copy()
    page  = int(query.pop('page', [1])[0]) # all values are lists in the QueryDict object and we never expect more than one
    
    return query, page

def browse(request):
    query, page = get_query_and_page(request)
    
    products = Product.objects.search(query)
    paginator = Paginator(products, BROWSE_PAGE_SIZE)
    
    try:
        paged_products = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paged_products = paginator.page(paginator.num_pages)

    try:
        next_page = paginator.page(page + 1)
    except (EmptyPage, InvalidPage):
        next_page = None

    left, mid, right = get_pagination(paginator, page)


    result = get_filter(request)
    result['pages'] = (paged_products, next_page,)
    result['templates'] = {
        'product_count': js_template(get_template_source('apparel/fragments/product_count.html')),
        'product': js_template(get_template_source('apparel/fragments/product_small.html')),
        'pagination': get_template_source('apparel/fragments/pagination_js.html')
    }
    result['pagination'] = {
        'left': left,
        'right': right,
        'mid': mid,
    }
    
    
    # FIXME: This could perhaps be moved out to a routine on its own. It is used
    # to collect the current query from the command line to enable options to
    # be pre-checked. The conversion from string to int for id-fields is required
    # to check wether they exist using the in-operator
    
    def _to_int(s):
        try:
            return int(s)
        except ValueError:
            return None
    
    qp   = QueryParser(Product)
    expr = {}
    for key, value in request.GET.items():
        try:
            label, short, field, operator = qp.parse_key(key)
        except InvalidExpression:
            continue
        
        expr['%s.%s' % (short, field)] = qp.prepare_op_val(operator, value)[1]
    
    result['selected_categories'] = filter(None, map(_to_int, expr.get('c.id') or []))
    result['selected_colors']     = expr.get('o.color')
    result['selected_brands']     = filter(None, map(_to_int, expr.get('m.id') or []))
    result['selected_price']      = expr.get('vp.price')
    result['selected_gender']     = expr.get('o.gender')
    
    return render_to_response('apparel/browse.html', result, context_instance=RequestContext(request))


def js_template(str):
    str = str.replace('{{', '<%=').replace('}}', '%>')
    str = re.sub(r'\{%\s*include "(.+?)"\s*%\}', lambda m: js_template(get_template_source(m.group(1))), str)
    
    return Template(str).render(Context())

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    viewed_products = request.session.get('viewed_products', [])
    try:
        viewed_products.remove(product.id)
    except ValueError:
        pass
    
    request.session['viewed_products'] = [product.id]
    request.session['viewed_products'].extend(viewed_products)
    
    for p in Product.objects.filter(pk__in=viewed_products):
        viewed_products[viewed_products.index(p.id)] = p
    
    user_looks = Look.objects.filter(user=request.user) if request.user.is_authenticated() else []
    
    return render_to_response(
            'apparel/product_detail.html',
            {
                'templates': {
                    'look_button': js_template(get_template_source('apparel/fragments/look_button.html'))
                },
                'object': product,
                'user_looks': user_looks,
                'looks_with_product': Look.objects.filter(products=product),
                'viewed_products': viewed_products,
                'object_url': request.build_absolute_uri()
            },
            context_instance=RequestContext(request),
            )

def look_detail(request, slug):
    look = get_object_or_404(Look, slug=slug)
    looks_by_user = Look.objects.filter(user=look.user).exclude(pk=look.id)
    similar_looks = [] #Recommender.objects.get_similar_items(look, User.objects.all(), Look.objects.all(), 0)
    return render_to_response(
            'apparel/look_detail.html',
            {
                'object': look,
                'looks_by_user': looks_by_user,
                'similar_looks': similar_looks,
                'tooltips': True,
                'object_url': request.build_absolute_uri()
            },
            context_instance=RequestContext(request),
        )


#@login_required - FIXME: Find out why this isn't working anymore
@seamless_request_handling
def look_edit(request, slug):
    look = get_object_or_404(Look, slug=slug)
    
    if request.method == 'POST':
        form = LookForm(request.POST, request.FILES, instance=look)
        #import pdb; pdb.set_trace()
        if form.is_valid():
            form.save()
    else:
        form = LookForm(instance=look)
    
    try:
        wardrobe = Wardrobe.objects.get(user=request.user).products.all()
    except Wardrobe.DoesNotExist:
        wardrobe = []
    
    data = {
        'object': form.instance, 
        'form': form,
        'wardrobe': wardrobe,
        'templates': {
            'look_collage_product': js_template(get_template_source('apparel/fragments/look_collage_product.html')),
            'product_thumb':        js_template(get_template_source('apparel/fragments/product_thumb.html')),
            'look_product_tooltip': js_template(get_template_source('apparel/fragments/look_product_tooltip.html')),
        }
    }
    
    return (
        data,
        render_to_response('apparel/look_edit.html', data, context_instance=RequestContext(request))
    )



def looks():
    pass

def get_template_source(template):
    print "*******"
    print template
    template_source, template_origin = find_template_source(template)
    return template_source



#def save_look_product(request):
#    try:
#        lp = LookProduct.objects.get(product__id=request.POST['product'], look__id=request.POST['look'])
#        form = LookProductForm(request.POST, instance=lp)
#    except LookProduct.DoesNotExist:
#        form = LookProductForm(request.POST)
#    form.save()
#    return HttpResponseRedirect(reverse('apparel.views.look_detail', args=(request.POST['look'],)))


@seamless_request_handling
@login_required
def save_look_component(request):
    """
    This view adds or updates a component for a look and product
    """
    
    try:
        lc = LookComponent.objects.get(
                    product__id=request.POST['product'],
                    look__id=request.POST['look'],
                    component_of=request.POST['component_of']
        )
        form  = LookComponentForm(request.POST, instance=lc)
        added = False
    except LookComponent.DoesNotExist:
        form  = LookComponentForm(request.POST)
        added = True
    
    if form.is_valid():
        # FIXME: This behaviour should be default in all forms. Implement this
        # globally somehow.
        for field in form.cleaned_data:
            if form.cleaned_data[field] is None and field not in form.data:
                form.cleaned_data[field] = form.initial.get(field)
        
        form.save()
    else:
        # FIXME: Return some error response here. Can we just throw an exception?
        raise Exception('Validaton errors %s' % form.errors)
    
    
    return (
        {'look_component': form.instance, 'added': added },                                       # JSON response 
        HttpResponseRedirect( reverse('apparel.views.look_edit', args=(request.POST['look'],)))   # Browser request response
    )
    


@seamless_request_handling
@login_required
def delete_look_component(request):
    """
    Removes a component from a look. This does *not* remove the product from the
    look
    """
    
    components = LookComponent.objects.filter(
        product__id=request.POST['product'],
        look__id=request.POST['look']
    )
    in_look = True
    
    if components.count() > 1:
        # Remove only selected component
        components.filter(component_of=request.POST['component_of']).delete()
    else:
        # Remove selected component AND product from look
        components[0].delete()
        Look.objects.get(pk=request.POST['look']).products.remove(request.POST['product'])
        in_look = False
    
    return (
        {
            'component': request.POST['component_of'],
            'in_look': in_look,
        }, 
        HttpResponseRedirect( reverse('apparel.views.look_edit', args=(request.POST['look'],)))
    )

@seamless_request_handling
@login_required
def add_to_look(request):
    if 'look' in request.POST:
        look = Look.objects.get(pk=request.POST['look'])
        created = False
    else:
        look = Look(user=request.user, title=request.POST.get('new_name'))
        look.save()
        created = True
    
    p = Product.objects.get(pk=request.POST.get('product'))
    
    if look.products.filter(pk=p.id):
        added = False
    else:
        added = True
        look.products.add(p)
    
    return (
        {
            'look': look,           # The look the product was added to
            'created': created,     # Whether the look was created
            'added': added,         # Whether the product was added to the look or not. If false it was aleady there.
        }, 
        HttpResponseRedirect(reverse('apparel.views.look_detail', args=(look.slug,)))
    )
    

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
