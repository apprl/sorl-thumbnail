import logging, re, math, copy
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed, HttpResponsePermanentRedirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext
from django.db.models import Q, Max, Min
from django.template import RequestContext, Template, Context, loader
from django.template.loader import find_template_source, get_template
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.views.generic import list_detail

from sorl.thumbnail.main import DjangoThumbnail
from hanssonlarsson.django.exporter import json
from recommender.models import Recommender
from voting.models import Vote

from apparel.decorators import seamless_request_handling, get_current_user
from apparel.manager import QueryParser, InvalidExpression
from apparel.models import *
from apparel.forms import *


BROWSE_PAGE_SIZE = 12
BROWSE_PAGE_MAX  = 100



def _to_int(s):
    try:
        return int(s)
    except ValueError:
        return None
    
# Used to collect the current query from the command line to enable options to
# be pre-checked. The conversion from string to int for id-fields is required
# to check wether they exist using the in-operator
def update_with_selected(context, request):
    qp   = QueryParser(Product)
    expr = {}
    for key, value in request.GET.items():
        try:
            label, short, field, operator = qp.parse_key(key)
        except InvalidExpression:
            continue
        
        expr['%s.%s' % (short, field)] = qp.prepare_op_val(operator, value)[1]
    
    context.update(
        selected_categories = filter(None, map(_to_int, expr.get('c.id') or [])),
        selected_colors     = expr.get('o.color'),
        selected_brands     = filter(None, map(_to_int, expr.get('m.id') or [])),
        selected_price      = expr.get('vp.price'),
        selected_gender     = expr.get('p.gender'),
    )

def search(request, model):
    """
    AJAX-only search results. Results are paginated
    """
    class_name = {
        'products': 'Product',
        'manufacturers': 'Manufacturer',
        'categories': 'Category',
        'looks': 'Look',
    }.get(model)
    
    paged_result = get_paged_search_result(request, class_name)
    response     = get_pagination_as_dict(paged_result)

    return HttpResponse(
        json.encode(response),
        mimetype='text/json'
    )

@get_current_user
def wardrobe(request, profile):
    return browse(request, template='profile/wardrobe.html', wardrobe__user=profile.user)

def without(query, model_shorthand):
    r = re.compile(r"^\d:%s\." % model_shorthand)

    return dict((k, v) for k, v in query.items() if not r.match(k))

def browse(request, template='apparel/browse.html', **kwargs):
    paged_result = get_paged_search_result(request,
        class_name='Product',
        page_size=BROWSE_PAGE_SIZE,
        **kwargs
    )
    
    try:
        next_page = paged_result.paginator.page(paged_result.next_page_number())
    except (EmptyPage, InvalidPage):
        next_page = None

    pages = (paged_result, next_page,)

    left, mid, right = get_pagination(paged_result.paginator, paged_result.number)
    pagination = {
        'left': left,
        'mid': mid,
        'right': right
    }

    result = get_filter(request, **kwargs)

    result.update(pagination=pagination)

    update_with_selected(result, request)

    if request.is_ajax():
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
        result.update(get_pagination_as_dict(paged_result))

        return HttpResponse(
            json.encode(result),
            mimetype='text/json'
        )
    
    result.update(
        current_page = paged_result,
        pages = pages,
        templates = {
            'pagination': get_template_source('apparel/fragments/pagination_js.html')
        },
    )

    return render_to_response(template, result, context_instance=RequestContext(request))

def product_redirect(request, pk):
    """
    Makes it
    """
    product = get_object_or_404(Product, pk=pk, published=True)
    return HttpResponsePermanentRedirect(product.get_absolute_url())

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, published=True)
    viewed_products = request.session.get('viewed_products', [])
    try:
        viewed_products.remove(product.id)
    except ValueError:
        pass
    
    request.session['viewed_products'] = [product.id]
    request.session['viewed_products'].extend(viewed_products)
    
    for p in Product.objects.filter(pk__in=viewed_products):
        viewed_products[viewed_products.index(p.id)] = p
    
    if request.user.is_authenticated():
        user_looks     = Look.objects.filter(user=request.user)
        try:
            is_in_wardrobe = Wardrobe.objects.get(user=request.user).products.filter(pk=product.id).count() > 0
        except Wardrobe.DoesNotExist:
            is_in_wardrobe = False
    else:
        user_looks     = []
        is_in_wardrobe = False
    
    context = RequestContext(request)
    
    return render_to_response(
            'apparel/product_detail.html',
            {
                'templates': {
                    'look_button': js_template(get_template_source('apparel/fragments/look_button.html'), context=context)
                },
                'object': product,
                'user_looks': user_looks,
                'is_in_wardrobe': is_in_wardrobe,
                'looks_with_product': Look.objects.filter(products=product),
                'viewed_products': viewed_products,
                'object_url': request.build_absolute_uri()
            },
            context_instance=context,
            )

def look_list(request, profile=None, contains=None, page=0):
    
    if profile:
        queryset = Look.objects.filter(user__username=profile)
    elif contains:
        queryset = Look.objects.filter(products__slug=contains)
    elif len(request.GET):
        queryset = Look.objects.search(request.GET)
    else:
        queryset = Look.objects.all().order_by('-modified')
    
    
    # FIXME: This is used elsewhere, we should move it out to a utils module
    popular = Vote.objects.get_top(Look, limit=8)
    
    return list_detail.object_list(
        request,
        queryset=queryset,
        paginate_by=10,
        page=page,
        extra_context={
            "popular_looks": popular
        }
    )

def look_detail(request, slug):
    look = get_object_or_404(Look, slug=slug)
    looks_by_user = Look.objects.filter(user=look.user).exclude(pk=look.id).order_by('-modified')[:8]
    similar_looks = []
    
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
    """
    GET  - Display edit look page
    POST - Save changes to a look
            - if in AJAX mode, return the look as JSON
            - else redirect to look's view page (unless a new image has been uploaded)
    """
    
    # FIXME: Ensure user owns look
    look = get_object_or_404(Look, slug=slug, user=request.user)
        
    if request.method == 'POST':
        form = LookForm(request.POST, request.FILES, instance=look)
        
        if form.is_valid():
            form.save()
            if not request.is_ajax() and not request.FILES:
                return HttpResponseRedirect(form.instance.get_absolute_url())
        else:
            logging.debug('Form errors: %s', form.errors.__unicode__())
    
    else:
        form = LookForm(instance=look)
    
    try:
        wardrobe = Wardrobe.objects.get(user=request.user).products.all()
    except Wardrobe.DoesNotExist:
        wardrobe = []
    
    context = RequestContext(request)
    
    data = {
        'object': form.instance, 
        'form': form,
        'wardrobe': wardrobe,
        'templates': {
            'product_thumb': js_template(get_template_source('apparel/fragments/product_thumb.html'), context=context),
        }
    }
    # FIXME: Cannot export Form objects as JSON. Fix this and remove this
    # work around
    json_data = data.copy()
    del json_data['form']
    return (
        json_data,
        render_to_response('apparel/look_edit.html', data, context_instance=context)
    )


@login_required
@seamless_request_handling
# FIXME: Require a POST to this page
def look_create(request):
    """
    POST - Save changes to a look
            - if in AJAX mode, return the look as JSON
            - else redirect to look's edit page (unless a new image has been uploaded)
    GET - Display create page
            - if in AJAX mode, this won't work  
    """
    
    if request.method == 'GET':
        return render_to_response('apparel/look_create.html', {}, context_instance=RequestContext(request))
    
    look = Look.objects.create(
        user=request.user, 
        title=request.POST.get('title'),
        description=request.POST.get('description')
    )
    
    return (
        look,
        HttpResponseRedirect( reverse('apparel.views.look_edit', args=(look.slug,)))
    )


def looks():
    pass

def get_template_source(template):
    template_source, template_origin = find_template_source(template)
    return template_source

def widget(request, object_id, template_name, model):
    try:
        instance = model.objects.get(pk=object_id)
        html     = get_template(template_name).render(RequestContext(request, {'object': instance}))
        success  = True
    except model.DoesNotExist:
        success  = False
        html     = 'Not found'

    return HttpResponse('%s(%s)' % (request.GET['callback'], json.encode({
        'success': success,
        'html':  html,
    })), mimetype='application/json')


@seamless_request_handling
@login_required
def save_look_component(request):
    """
    This view adds or updates a component for a look and product
    """
    
    look = get_object_or_404(Look, pk=request.POST['look'], user=request.user)
    
    try:
        lc = LookComponent.objects.get(
                    look=look,
                    product__id=request.POST['product'],
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
                setattr(form.instance, field, form.initial.get(field))
        
        if not form.instance.top and not form.instance.left:
            components = LookComponent.objects.filter(positioned='A', look=look, component_of=form.instance.component_of)
            left = components.aggregate(Max('left')).values()[0]
            top  = components.aggregate(Max('top')).values()[0]
            
            form.instance.left = 0 if left is None else left + 78 
            form.instance.top  = 0 if top  is None else top 
            
            if form.instance.left > 78 * 5:
                form.instance.top += 150
                form.instance.left = 0
            
            form.instance.positioned = 'A'
        else:
            form.instance.positioned = 'M'
        
        form.save()
    else:
        # FIXME: Return some error response here. Can we just throw an exception?
        raise Exception('Validaton errors %s' % form.errors)
    
    template = 'look_collage_product' if form.instance.component_of == 'C' else 'look_photo_product'
    return (
        {
            'look_component': form.instance,
            'added': added,
            'html': loader.render_to_string('apparel/fragments/%s.html' % template, {'component': form.instance}, context_instance=RequestContext(request)),
        },                                                                                        # JSON response 
        HttpResponseRedirect( reverse('apparel.views.look_edit', args=(request.POST['look'],)))   # Browser request response
    )

@seamless_request_handling
@login_required
def delete_look_component(request):
    """
    Removes a list of components from for the given look. 
    Parameters:
     - product (ID, ID, ...)
     - component_of C or P
     - look (ID)
     - delete_photo (True, False) - removes the associated photo. component_of will have to be P for this to work
    
    AJAX return value
     - component: C or P
     - in_look:
        id: True or False,
        ...
    """
    
    # NOTE: This is a workaround because jQuery adds the [] notation to arrays,
    # rather than just add multiple keys like a normal user agent
    products = request.POST.getlist('product[]') if 'product[]' in request.POST else request.POST.getlist('product')
    look     = get_object_or_404(Look, pk=request.POST['look'], user=request.user)
    
    components = LookComponent.objects.filter(
        product__id__in=products,
        look=look
    )
    
    # Delete all components for the current context
    components.filter(component_of=request.POST['component_of']).delete()
    
    # Make a list of which ones are still on the look
    in_look = dict( map(lambda x: (x, components.filter(product__id=x).exists()), products) )
    
    # Remove the ones who aren't
    look.products.remove(*[x for x in in_look.keys() if not in_look[x]])
    
    # Delete photo if told to do so
    if request.POST.get('delete_photo') and request.POST['component_of'] == 'P':
        look.image = None
        look.save()
    
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

    if request.POST.get('look'):
        look = get_object_or_404(Look, pk=request.POST['look'], user=request.user)
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
    
    add_to_wardrobe(request)        # Also, add the product to user's wardrobe
    
    return (
        {
            'look': look,           # The look the product was added to
            'created': created,     # Whether the look was created
            'added': added,         # Whether the product was added to the look or not. If false it was aleady there.
            'html': loader.render_to_string('apparel/fragments/look_small_sidebar.html', {'object': look, 'hide_like_button': False}, context_instance=RequestContext(request)),
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
    wardrobe.products.add(Product.objects.get(pk=request.POST.get('product')))
    wardrobe.save() # FIXME: Only save if created?
    
    return wardrobe
    
    
def csrf_failure(request, reason=None):
    """
    Display error page for cross site forgery requests
    """
    if reason is None: reason = '[None given]'
    logging.debug("CSRF failure: %s" % reason)
    return render_to_response('403.html', { 'is_csrf': True, 'debug': settings.DEBUG, 'reason': reason }, context_instance=RequestContext(request))





#
# Utility routines. FIXME: Move these out
#

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

def get_paged_search_result(request, class_name=None, page_size=None, **kwargs):
    try:
        model_class = eval(class_name)
    except TypeError:
        raise Exception("No model to search for")
    except:
        raise
    
    query, page, size = get_query_and_page(request, page_size)
        
    paginator = Paginator(model_class.objects.search(query).filter(**kwargs), size)
    
    try:
        paged_result = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paged_result = paginator.page(paginator.num_pages)
    
    return paged_result
    
def get_pagination_as_dict(paged_result):
    # FIXME: This exists because the JSON exporter is unable to serialise
    # Page and Pagination objects. Perhaps this code could be moved to the 
    # exporter module instead?
    return {
        'object_list': paged_result.object_list,
        'previous_page_number': paged_result.previous_page_number(),
        'next_page_number': paged_result.next_page_number(),
        'number': paged_result.number,
        'paginator': {
            'num_pages': paged_result.paginator.num_pages,
            'count': paged_result.paginator.count,
        },
    }

def get_pricerange(query, **kwargs):
    query_set = VendorProduct.objects.filter(product__published=True)
    filter_query = without(query, 'vp')

    if filter_query:
        query_set = query_set.filter(product__in=Product.objects.search(filter_query))
    if kwargs:
        query_set = query_set.filter(**kwargs)

    pricerange = query_set.aggregate(min=Min('price'), max=Max('price'))

    if pricerange['min'] is None:
        pricerange['min'] = 0
    else:
        pricerange['min'] = int(100 * math.floor(float(pricerange['min']) / 100))
    if pricerange['max'] is None:
        pricerange['max'] = 10000
    else:
        pricerange['max'] = int(100 * math.ceil(float(pricerange['max']) / 100))
    pricerange['selected'] = query['1:vp.price:range'] if '1:vp.price:range' in query else '%s,%s' % (pricerange['min'],pricerange['max'])

    return pricerange

def get_filter(request, **kwargs):
    query = request.GET.copy()
    if 'criterion' in query:
        del query['criterion']
    if 'page' in query:
        del query['page']

    colors = Option.objects.filter(option_type__name__iexact='color', product__published=True)

    if query or kwargs:
        if query:
            manufacturers = Product.objects.search(without(query, 'm')).filter(published=True)
            colors = colors.filter(product__in=Product.objects.search(without(query, 'o')))
        else:
            manufacturers = Product.objects.filter(published=True)

        if kwargs:
            manufacturers = manufacturers.filter(**kwargs)
            colors = colors.filter(**kwargs)

        manufacturers = manufacturers.distinct().values_list('manufacturer', flat=True)

        if not request.is_ajax():
            manufacturers = Manufacturer.objects.filter(id__in=manufacturers)

    else:
        manufacturers = Manufacturer.objects.filter(product__published=True).distinct()

    result = {}

    if request.is_ajax():
        colors = colors.values_list('value', flat=True)
    else:
        result.update(categories_all=Category._tree_manager.all())

    if query or kwargs:
        result.update(
            categories = Product.objects.search(without(query, 'c')).filter(published=True).filter(**kwargs).distinct().values_list('category', flat=True)
        )

    result.update(
        manufacturers = manufacturers,
        colors = colors,
        pricerange = get_pricerange(query, **kwargs),
    )

    return result

def index(request):
    ctx = get_filter(request)
    # FIXME: This just selects the top voted objects. We should implement a better popularity algorithm, see #69
    ctx['popular_looks']  = Vote.objects.get_top(Look, limit=6)    
    ctx['categories_all']     = ctx['categories_all'].filter(on_front_page=True)
    ctx['featured_looks'] = Look.featured.all().order_by('-modified')[:settings.APPAREL_LOOK_FEATURED]
    
    return render_to_response('index.html', ctx, context_instance=RequestContext(request))

def get_query_and_page(request, override_size=None):
    """
    Copies the request query to a mutable dict and removes the 'page' and 'size'
    keys.
     - 'page' - indicates which page in the paged result should be used
     - 'size' - indicates page size used. 'max' corresponds to the BROWSE_PAGE_MAX
                setting.
    
    If 'override_size' argument is passed, the 'size' query key have no effect.
    """
    query = request.GET.copy()
    page  = int(query.pop('page', [1])[0]) # all values are lists in the QueryDict object and we never expect more than one
    size  = query.pop('size', ['max'])[0]
    
    if page == -1:
        logging.warn('Use of depricated page=-1 query. Use size=MAX instead. Request %s', request)
        size = 'max'
        page = 1
    
    if override_size is not None:
        size = override_size
        logging.debug('Using explicit page size: %s', override_size)
    elif size == 'max':
        size = BROWSE_PAGE_MAX
        logging.debug('Using max page size: %s', size)
    elif size:
        try:
            size = int(size)
        except ValueError:
            logging.error('%s is not an intiger, using max setting', size)
            size = BROWSE_PAGE_MAX
        else:
            if size > BROWSE_PAGE_MAX: size = BROWSE_PAGE_MAX
        
        logging.debug('Using query page size: %s', size)
    
    return query, page, size


def js_template(str, request=None, context=None):
    if context is None:
        context = RequestContext(request)
    
    str = str.replace('{{', '${').replace('}}', '}')
    str = re.sub(r'\{%\s*include "(.+?)"\s*%\}', lambda m: js_template(get_template_source(m.group(1)), context=context), str)

    return Template(str).render(context)
