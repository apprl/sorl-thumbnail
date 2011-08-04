import logging
import re
import math
import json

from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponsePermanentRedirect
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db.models import Q, Max, Min, Count, Sum, connection, signals
from django.template import RequestContext, loader
from django.template.loader import get_template
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.views.generic import list_detail
from django.views.i18n import set_language
from hanssonlarsson.django.exporter import json as special_json
from actstream.models import user_stream, Follow
from haystack.query import SearchQuerySet

from apparelrow.tasks import search_index_update_task
from apparelrow.profile.models import ApparelProfile
from apparelrow.apparel.decorators import seamless_request_handling
from apparelrow.apparel.decorators import get_current_user
from apparelrow.apparel.models import Product, ProductLike, Manufacturer, Category, Option, VendorProduct
from apparelrow.apparel.models import Look, LookLike, LookComponent, Wardrobe, FirstPageContent
from apparelrow.apparel.forms import LookForm, LookComponentForm
import apparel.signals

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
                'object': product,
                'user_looks': user_looks,
                'is_in_wardrobe': is_in_wardrobe,
                'looks_with_product': Look.objects.filter(products=product),
                'viewed_products': viewed_products,
                'object_url': request.build_absolute_uri()
            },
            context_instance=context,
            )

@login_required
def product_like(request, slug, action):
    """
    Like or unlike a product through ajax.
    """
    if request.method == 'GET':
        return HttpResponse(json.dumps(dict(success=False, error_message='POST only')))
    if not request.user.is_authenticated():
        return HttpResponse(json.dumps(dict(success=False, error_message='Not authenticated')))

    try:
        product = Product.objects.get(slug=slug)
    except Product.MultipleObjectsReturned, Product.DoesNotExist:
        return HttpResponse(json.dumps(dict(success=False, error_message='No product found')))

    if action == 'like':
        product_like, created = ProductLike.objects.get_or_create(user=request.user, product=product)
        product_like.active = True
        product_like.save()

        apparel.signals.like.send(sender=ProductLike, instance=product_like, request=request)
        return HttpResponse(json.dumps(dict(success=True, error_message=None)))

    elif action == 'unlike':
        product_like, created = ProductLike.objects.get_or_create(user=request.user, product=product)
        product_like.active = False
        product_like.save()

        apparel.signals.unlike.send(sender=ProductLike, instance=product_like, request=request)
        return HttpResponse(json.dumps(dict(success=True, error_message=None)))

    return HttpResponse(json.dumps(dict(success=False, error_message='Unknown')))

@login_required
def look_like(request, slug, action):
    """
    Like or unlike a look through ajax.
    """
    if request.method == 'GET':
        return HttpResponse(json.dumps(dict(success=False, error_message='POST only')))
    if not request.user.is_authenticated():
        return HttpResponse(json.dumps(dict(success=False, error_message='Not authenticated')))

    try:
        look = Look.objects.get(slug=slug)
    except Look.MultipleObjectsReturned, Look.DoesNotExist:
        return HttpResponse(json.dumps(dict(success=False, error_message='No look found')))

    if action == 'like':
        look_like, created = LookLike.objects.get_or_create(user=request.user, look=look)
        look_like.active = True
        look_like.save()

        apparel.signals.like.send(sender=LookLike, instance=look_like, request=request)
        return HttpResponse(json.dumps(dict(success=True, error_message=None)))

    elif action == 'unlike':
        look_like, created = LookLike.objects.get_or_create(user=request.user, look=look)
        look_like.active = False
        look_like.save()

        apparel.signals.unlike.send(sender=LookLike, instance=look_like, request=request)
        return HttpResponse(json.dumps(dict(success=True, error_message=None)))

    return HttpResponse(json.dumps(dict(success=False, error_message='Unknown')))


def look_list(request, popular=None, contains=None, page=0):
    """
    This view can list looks in three ways:

        1) If no argument is used a list of all looks is displayed.
        3) If popular-argument is set displays a list of all popular looks in your network.
        2) If contains-argument is set displays all looks that contains the product.

    """
    if contains:
        queryset = Look.objects.filter(products__slug=contains)
    elif popular:
        if request.user.is_authenticated():
            user_ids = Follow.objects.filter(user=request.user, content_type=ContentType.objects.get_for_model(User)).values_list('object_id', flat=True)
            queryset = Look.objects.filter(Q(likes__active=True) & Q(user__in=user_ids)).annotate(num_likes=Count('likes')).order_by('-num_likes')
        else:
            queryset = Look.objects.filter(likes__active=True).annotate(num_likes=Count('likes')).order_by('-num_likes')
    else:
        queryset = Look.objects.all().order_by('-modified')

    popular = get_top_looks(limit=8)

    if request.user.is_authenticated():
        user_ids = Follow.objects.filter(user=request.user).values_list('object_id', flat=True)
        most_looks_users = ApparelProfile.objects.annotate(look_count=Count('user__look')).order_by('-look_count').filter(look_count__gt=1, user__in=user_ids)
    else:
        most_looks_users = None

    return list_detail.object_list(
        request,
        queryset=queryset,
        paginate_by=10,
        extra_context={
            'next': request.get_full_path(),
            'previous': None,
            'popular_looks': popular,
            'most_looks_users': most_looks_users
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
        'wardrobe': wardrobe
    }
    # FIXME: Cannot export Form objects as JSON. Fix this and remove this
    # work around
    json_data = data.copy()
    del json_data['form']
    return (
        json_data,
        render_to_response('apparel/look_edit.html', data, context_instance=context)
    )

def look_create(request):
    """
    POST - Save changes to a look
            - if in AJAX mode, return the look as JSON
            - else redirect to look's edit page (unless a new image has been uploaded)
    GET - Display create page
            - if not logged in display a popup
            - if in AJAX mode, this won't work
    """

    if request.method == 'GET' and request.user.is_authenticated():
        return render_to_response('apparel/look_create.html', {}, context_instance=RequestContext(request))

    if request.method == 'POST' and request.user.is_authenticated():
        look = Look.objects.create(
            user=request.user,
            title=request.POST.get('title'),
            description=request.POST.get('description')
        )
        if request.is_ajax():
            return HttpResponse(json.encode({'success': True, 'data': look}), mimetype='text/json')

        return HttpResponseRedirect(reverse('apparel.views.look_edit', args=(look.slug,)))

    return render_to_response('apparel/fragments/dialog_create_look.html', {}, context_instance=RequestContext(request))

@login_required
@seamless_request_handling
def look_delete(request, slug):
    look = get_object_or_404(Look, slug=slug, user=request.user)
    if look:
        look.delete()
        return (True, HttpResponseRedirect(reverse('profile.views.looks', args=(request.user.username,))))
    else:
        return (False, HttpResponseRedirect(reverse('profile.views.looks', args=(request.user.username,))))

def looks():
    pass

def widget(request, object_id, template_name, model):
    try:
        instance = model.objects.get(pk=object_id)
        html     = get_template(template_name).render(RequestContext(request, {'object': instance}))
        success  = True
    except model.DoesNotExist:
        success  = False
        html     = 'Not found'

    return HttpResponse('%s(%s)' % (request.GET['callback'], special_json.encode({
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
    
    template = 'look_collage_product_image' if form.instance.component_of == 'C' else 'look_photo_product'
    return (
        {
            'look_component': form.instance,
            'added': added,
            'html': loader.render_to_string('apparel/fragments/%s.html' % template, {'component': form.instance}, context_instance=RequestContext(request)),
        },                                                                                        # JSON response 
        HttpResponseRedirect(reverse('apparel.views.look_edit', args=(request.POST['look'],)))   # Browser request response
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
        HttpResponseRedirect(reverse('apparel.views.look_edit', args=(request.POST['look'],)))
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
            'created_html': loader.render_to_string('apparel/fragments/look_button.html', {'look': look}, context_instance=RequestContext(request)),
            'added': added,         # Whether the product was added to the look or not. If false it was aleady there.
            'html': loader.render_to_string('apparel/fragments/look_small_like.html', {'object': look}, context_instance=RequestContext(request)),
        },
        HttpResponseRedirect(reverse('apparel.views.look_detail', args=(look.slug,)))
    )
    

@seamless_request_handling
@login_required
def add_to_wardrobe(request):
    """
    Adds a product to a user's wardrobe (and creates it if necessary)
    """
    product = Product.objects.get(pk=request.POST.get('product'))
    wardrobe, created = Wardrobe.objects.get_or_create(user=request.user)
    wardrobe.products.add(product)
    search_index_update_task.delay(product._meta.app_label, product._meta.module_name, product._get_pk_val()) # Update search index
    
    return {'success': True}

@seamless_request_handling
@login_required
def delete_from_wardrobe(request):
    product = Product.objects.get(pk=request.POST.get('product'))
    wardrobe, created = Wardrobe.objects.get_or_create(user=request.user)
    wardrobe.products.remove(product)
    search_index_update_task.delay(product._meta.app_label, product._meta.module_name, product._get_pk_val()) # Update search index

    return ({'success': True}, HttpResponseRedirect(reverse('apparel.browse.browse_wardrobe', args=(request.user,))))
    
def csrf_failure(request, reason=None):
    """
    Display error page for cross site forgery requests
    """
    if reason is None: reason = '[None given]'
    logging.debug("CSRF failure: %s" % reason)
    return render_to_response('403.html', { 'is_csrf': True, 'debug': settings.DEBUG, 'reason': reason }, context_instance=RequestContext(request))

def user_list(request):
    """
    Displays a list of profiles
    """
    queryset = ApparelProfile.objects.filter(user__is_active=True).order_by('user__first_name', 'user__last_name', 'user__username')

    paginator = Paginator(queryset, 10)
    try:
        paged_result = paginator.page(int(request.GET.get('page', 1)))
    except (EmptyPage, InvalidPage):
        paged_result = paginator.page(paginator.num_pages)
    except ValueError:
        paged_result = paginator.page(1)

    # FIXME: This does not work so well with pagination... solve in query instead, but how?
    #object_list = sorted(paged_result.object_list, key=lambda x: x.display_name)
    object_list = paged_result.object_list

    context = {'page_obj': paged_result,
               'page_range': paginator.page_range,
               'object_list': object_list,
               'facebook_friends': get_facebook_friends(request),
               'most_followed_users': get_most_followed_users(limit=10)}

    return render_to_response('apparel/users.html', context, context_instance=RequestContext(request))

@get_current_user
@login_required
def home(request, profile, page=0):
    """
    Displays the logged in user's page
    """
    queryset = user_stream(request.user)
    queryset = queryset.filter(verb__in=['liked_look', 'liked_product', 'added', 'commented', 'created'])

    # Retrieve most popular products in users network
    limit = 2
    user_ids = list(Follow.objects.filter(user=request.user).values_list('object_id', flat=True)) + [0]
    user_ids_or = ' OR '.join(str(x) for x in user_ids)
    search_queryset = SearchQuerySet().narrow('user_likes:({0}) OR user_wardrobe:({0})'.format(user_ids_or)).order_by('-popularity')[:limit]
    popular_products_in_network = [x.object for x in search_queryset if x]

    return list_detail.object_list(
        request,
        queryset=queryset,
        template_name='apparel/user_home.html',
        paginate_by=10,
        page=page,
        extra_context={
            'next': request.get_full_path(),
            'profile': profile,
            'facebook_friends': get_facebook_friends(request),
            'popular_looks_in_network': get_top_looks_in_network(request.user, limit=2),
            'popular_products_in_network': [x.object for x in search_queryset if x]

        }
    )

def product_user_like_list(request, slug):
    product = Product.objects.get(slug=slug)
    queryset = ApparelProfile.objects.select_related('user').filter(Q(user__product_likes__product=product) & Q(user__product_likes__active=True)).order_by('user__first_name', 'user__last_name', 'user__username')
    return render_to_response(
        'apparel/fragments/product_user_like_list.html',
        {'profiles': queryset, 'slug': slug},
        context_instance=RequestContext(request)
    )

def look_user_like_list(request, slug):
    look = Look.objects.get(slug=slug)
    queryset = ApparelProfile.objects.select_related('user').filter(Q(user__look_likes__look=look) & Q(user__look_likes__active=True)).order_by('user__first_name', 'user__last_name', 'user__username')
    return render_to_response(
        'apparel/fragments/look_user_like_list.html',
        {'profiles': queryset, 'slug': slug},
        context_instance=RequestContext(request)
    )

def dialog_login_favorite_friends(request):
    """
    Display a dialog tailored for the browse page with information about
    facebook login. On successful login redirect to browse page with f=1.
    """
    return render_to_response('apparel/fragments/dialog_login_favorite_friends.html',
            {'next': reverse('apparel.browse.browse_products') + '#f=1'}, context_instance=RequestContext(request))

def dialog_like_product(request):
    """
    Display a dialog tailored for the product detail page with information
    about facebook login. On successful login redirect to same page.
    """
    return render_to_response('apparel/fragments/dialog_like_product.html',
            {'next': request.GET.get('next', '/')}, context_instance=RequestContext(request))

def dialog_like_look(request):
    """
    Display a dialog tailored for the look detail page with information about
    facebook login. On successful login redirect to same page.
    """
    return render_to_response('apparel/fragments/dialog_like_look.html',
            {'next': request.GET.get('next', '/')}, context_instance=RequestContext(request))

def dialog_follow_user(request):
    """
    Display a dialog tailored for the look detail page with information about
    facebook login. On successful login redirect to same page.
    """
    return render_to_response('apparel/fragments/dialog_follow_user.html',
            {'next': request.GET.get('next', '/')}, context_instance=RequestContext(request))

def index(request):
    #ctx = get_filter(request)
    ctx = {}
    # FIXME: This just selects the top voted objects. We should implement a better popularity algorithm, see #69
    ctx['pages'] = FirstPageContent.published_objects.all()
    ctx['popular_looks'] = get_top_looks(limit=6)
    ctx['all_colors'] = Option.objects.filter(option_type__name='color')
    ctx['categories_all'] = Category._tree_manager.filter(on_front_page=True)
    ctx['featured_looks'] = Look.featured.all().order_by('-modified')[:settings.APPAREL_LOOK_FEATURED]

    pricerange = VendorProduct.objects.filter(product__published=True, product__category__isnull=False).aggregate(min=Min('price'), max=Max('price'))
    if pricerange['min'] is None:
        pricerange['min'] = 0
    else:
        pricerange['min'] = int(pricerange['min'])
    if pricerange['max'] is None:
        pricerange['max'] = 10000
    else:
        pricerange['max'] = int(pricerange['max'])
    pricerange['selected'] = '%s,%s' % (pricerange['min'], pricerange['max'])
    ctx['pricerange'] = pricerange

    mp = Paginator(Manufacturer.objects.filter(product__published=True).distinct().order_by('name'), settings.APPAREL_MANUFACTURERS_PAGE_SIZE)
    try:
        manufacturers = mp.page(1).object_list
    except EmptyPage:
        manufacturers = []
    ctx['manufacturers'] = manufacturers

    return render_to_response('index.html', ctx, context_instance=RequestContext(request))

def apparel_set_language(request):
    language = request.POST.get('language', None)
    profile = request.user.get_profile()
    profile.language = language
    profile.save()

    return set_language(request)

#
# Utility routines. FIXME: Move these out
#

def get_top_looks(limit=10):
    return Look.objects.filter(likes__active=True).annotate(num_likes=Count('likes')).order_by('-num_likes').filter(num_likes__gt=0)[:limit]

def get_most_followed_users(limit=2):
    #object_ids = [x['object_id'] for x in Follow.objects.values('object_id').annotate(Count('id')).order_by('-id__count')[:limit]]
    #return ApparelProfile.objects.select_related('user').filter(user__in=object_ids)
    # FIXME: This is inefficient because it creates a query for everyone object_id, better solution?
    apparel_profiles = []
    for object_id in Follow.objects.values_list('object_id', flat=True).annotate(count=Count('id')).order_by('-count')[:limit]:
        apparel_profiles.append(ApparelProfile.objects.select_related('user').get(user__id=object_id))
    return apparel_profiles

def get_top_looks_in_network(user, limit=2):
    content_type = ContentType.objects.get_for_model(User)
    user_ids = Follow.objects.filter(content_type=content_type, user=user).values_list('object_id', flat=True)
    return Look.objects.filter(Q(likes__active=True) & Q(user__in=user_ids)).annotate(num_likes=Count('likes')).order_by('-num_likes')[:limit]

def get_facebook_friends(request):
    if request.user.is_authenticated() and request.facebook:
        friends = request.facebook.graph.get_connections('me', 'friends')
        friends_uids = [f['id'] for f in friends['data']]
        return ApparelProfile.objects.filter(user__facebookprofile__uid__in=friends_uids)
