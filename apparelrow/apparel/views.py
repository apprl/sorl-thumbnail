# -*- coding: utf-8 -*-
import logging
import re
import math
import json
import string
import unicodedata
import datetime
import csv
import StringIO

from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponsePermanentRedirect, HttpResponseNotFound
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db.models import Q, Max, Min, Count, Sum, connection, signals, get_model
from django.template import RequestContext, loader
from django.template.loader import get_template
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.views.i18n import set_language
from django.utils import translation
from django.utils.encoding import smart_unicode
from hanssonlarsson.django.exporter import json as special_json
from actstream.models import Follow, Action
from sorl.thumbnail import get_thumbnail

from profile.models import ApparelProfile
from profile.utils import get_facebook_user
from apparel.decorators import seamless_request_handling
from apparel.decorators import get_current_user
from apparel.models import Product, ProductLike, Manufacturer, Category, Option, VendorProduct, BackgroundImage
from apparel.models import Look, LookLike, LookComponent, FirstPageContent
from apparel.forms import LookForm, LookComponentForm
from apparel.search import ApparelSearch
from apparel.search import more_like_this_product
from apparel.utils import get_pagination_page, get_gender_from_cookie, CountPopularity
from profile.notifications import process_like_look_created

FAVORITES_PAGE_SIZE = 30
LOOK_PAGE_SIZE = 10

def product_redirect(request, pk):
    """
    Makes it
    """
    product = get_object_or_404(Product, pk=pk, published=True)
    return HttpResponsePermanentRedirect(product.get_absolute_url())

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, published=True, gender__isnull=False)
    viewed_products = request.session.get('viewed_products', [])
    try:
        viewed_products.remove(product.id)
    except ValueError:
        pass

    request.session['viewed_products'] = [product.id]
    request.session['viewed_products'].extend(viewed_products)

    for p in Product.objects.filter(pk__in=viewed_products):
        viewed_products[viewed_products.index(p.id)] = p

    is_in_wardrobe = False
    user_looks = []
    if request.user.is_authenticated():
        user_looks = Look.objects.filter(user=request.user)
        is_in_wardrobe = ProductLike.objects.filter(user=request.user, product=product, active=True).exists()

    looks_with_product = Look.objects.filter(components__product=product).order_by('-modified')[:2]
    looks_with_product_count = Look.objects.filter(components__product=product).aggregate(Count('id')).get('id__count', 0)

    # Comments
    content_type =ContentType.objects.get_for_model(Product)
    comments =  Comment.objects.filter(content_type=content_type, object_pk=product.pk, is_public=True, is_removed=False).select_related('user', 'user__profile')

    # Likes
    likes = product.likes.filter(active=True).order_by('-modified').select_related('user', 'user__profile')

    return render_to_response(
            'apparel/product_detail.html',
            {
                'object': product,
                'user_looks': user_looks,
                'is_in_wardrobe': is_in_wardrobe,
                'looks_with_product': looks_with_product,
                'looks_with_product_count': looks_with_product_count,
                'viewed_products': viewed_products,
                'object_url': request.build_absolute_uri(),
                'more_like_this': more_like_this_product(product.id, product.gender, 20),
                'comments': comments,
                'likes': likes
            }, context_instance=RequestContext(request),
        )

def product_popup(request):
    product_ids = []
    try:
        product_ids = map(int, request.GET.get('id', '').split(','))
    except ValueError:
        pass

    result = []

    content_type = ContentType.objects.get_for_model(Product)
    for product in product_ids:
        product_result = {'liked': False}
        if request.user and request.user.is_authenticated():
            product_result['liked'] = ProductLike.objects.filter(product=product, active=True, user=request.user).exists()
        product_result['likes'] = ProductLike.objects.filter(product=product, active=True).count()
        product_result['comments'] = Comment.objects.filter(content_type=content_type, object_pk=product, is_removed=False, is_public=True).count()
        #product_result['users'] = []

        #product_like_qs = ProductLike.objects.filter(product=product, active=True).order_by('-created')[:4]
        #comments_qs = Comment.objects.filter(content_type=content_type, object_pk=product.pk, is_removed=False, is_public=True).order_by('-submit_date')[:4]
        #combined_result = product_like_qs + comments_qs

        #for product_like in product_like_qs:
            #product_result['users'].append({
                #'id': product_like.user.pk,
                #'name': product_like.user.get_profile().display_name,
                #'url': product_like.user.get_profile().get_absolute_url(),
                #'image': product_like.user.get_profile().avatar})
        result.append(product_result)

    return HttpResponse(json.dumps(result), mimetype='application/json')


@login_required
def product_unlike(request):
    try:
        product = Product.objects.get(pk=request.POST.get('product', 0))
    except Product.MultipleObjectsReturned, Product.DoesNotExist:
        return HttpResponse(json.dumps(dict(success=False, error_message='No product found')), mimetype='application/json')

    product_like, created = ProductLike.objects.get_or_create(user=request.user, product=product)
    product_like.active = False
    product_like.save()

    return HttpResponse(json.dumps(dict(success=True, error_message=None)), mimetype='application/json')

def product_action(request, pk, action):
    """
    Like or unlike a product through ajax.
    """
    if not request.user or not request.user.is_authenticated():
        return HttpResponse(json.dumps(dict(success=False, error_message='Not authenticated')), mimetype='application/json')
    if request.method == 'GET':
        return HttpResponse(json.dumps(dict(success=False, error_message='Requires POST')), mimetype='application/json')
    if action not in ['like', 'unlike']:
        return HttpResponse(json.dumps(dict(success=False, error_message='Unknown command')), mimetype='application/json')

    try:
        product = Product.objects.get(pk=pk)
    except Product.MultipleObjectsReturned, Product.DoesNotExist:
        return HttpResponse(json.dumps(dict(success=False, error_message='No product found')), mimetype='application/json')

    product_like, created = ProductLike.objects.get_or_create(user=request.user, product=product)
    product_like.active = True if action == 'like' else False
    product_like.save()

    return HttpResponse(json.dumps(dict(success=True, error_message=None)), mimetype='application/json')

@login_required
def product_like(request, slug, action):
    """
    Like or unlike a product through ajax.
    """
    if not request.user.is_authenticated():
        return HttpResponse(json.dumps(dict(success=False, error_message='Not authenticated')), mimetype='application/json')
    if request.method == 'GET':
        return HttpResponse(json.dumps(dict(success=False, error_message='Requires POST')), mimetype='application/json')
    if action not in ['like', 'unlike']:
        return HttpResponse(json.dumps(dict(success=False, error_message='Unknown command')), mimetype='application/json')

    try:
        product = Product.objects.get(slug=slug)
    except Product.MultipleObjectsReturned, Product.DoesNotExist:
        return HttpResponse(json.dumps(dict(success=False, error_message='No product found')), mimetype='application/json')

    product_like, created = ProductLike.objects.get_or_create(user=request.user, product=product)
    product_like.active = True if action == 'like' else False
    product_like.save()

    return HttpResponse(json.dumps(dict(success=True, error_message=None)), mimetype='application/json')

@login_required
def look_like(request, slug, action):
    """
    Like or unlike a look through ajax.
    """
    if request.method == 'GET':
        return HttpResponse(json.dumps(dict(success=False, error_message='POST only')), mimetype='application/json')
    if not request.user.is_authenticated():
        return HttpResponse(json.dumps(dict(success=False, error_message='Not authenticated')), mimetype='application/json')
    if action not in ['like', 'unlike']:
        return HttpResponse(json.dumps(dict(success=False, error_message='Unknown command')), mimetype='application/json')

    try:
        look = Look.objects.get(slug=slug)
    except Look.MultipleObjectsReturned, Look.DoesNotExist:
        return HttpResponse(json.dumps(dict(success=False, error_message='No look found')), mimetype='application/json')

    look_like, created = LookLike.objects.get_or_create(user=request.user, look=look)
    look_like.active = True if action == 'like' else False
    look_like.save()

    if action == 'like':
        process_like_look_created.delay(look.user, request.user, look_like)

    return HttpResponse(json.dumps(dict(success=True, error_message=None)), mimetype='application/json')

def brand_list(request, gender=None):
    """
    List all brands.
    """
    alphabet = [u'#'] + list(unicode(string.ascii_lowercase)) + [u'å', u'ä', u'ö']
    brands = []
    brands_mapper = {}
    for index, alpha in enumerate(alphabet):
        brands_mapper[alpha] = index
        brands.append([alpha, False, []])

    if not gender:
        gender = get_gender_from_cookie(request)

    query_arguments = {'fl': 'manufacturer_auto, manufacturer_id',
                       'fq': ['django_ct:apparel.product', 'availability:true', 'published:true', 'gender:(U OR %s)' % (gender,)],
                       'start': 0,
                       'rows': -1,
                       'group': 'true',
                       'group.field': 'manufacturer_id'}
    for brand in ApparelSearch('*:*', **query_arguments).get_docs():
        if hasattr(brand, 'manufacturer_auto') and hasattr(brand, 'manufacturer_id'):
            brand_name = brand.manufacturer_auto
            brand_id = brand.manufacturer_id

            if brand_name:
                normalized_name = unicodedata.normalize('NFKD', smart_unicode(brand_name)).lower()
                for index, char in enumerate(normalized_name):
                    if char in alphabet:
                        brands[brands_mapper[char]][2].append({'id': brand_id, 'name': brand_name})
                        break
                    elif char.isdigit():
                        brands[brands_mapper[u'#']][2].append({'id': brand_id, 'name': brand_name})
                        break

    for index, alpha in enumerate(alphabet):
        brands[index][1] = len(brands[index][2]) == 0
        brands[index][2] = sorted(brands[index][2], key=lambda k: k['name'])

    # Popular brands with products
    popular_brands = []
    manufacturers = Product.valid_objects.filter(gender__in=[gender, 'U']) \
                                         .values_list('manufacturer', 'manufacturer__name') \
                                         .annotate(Count('manufacturer')) \
                                         .order_by('-popularity', '-date_added')[:10]
    for manufacturer in manufacturers:
        popular_brands.append([manufacturer[0],
                               manufacturer[1],
                               Product.valid_objects.filter(gender__in=[gender, 'U'],
                                                            manufacturer=manufacturer[0]) \
                                                    .order_by('-popularity', '-date_added')[:2]])

    # Popular brands in your network with products
    popular_brands_in_network = []
    user_ids = []
    if request.user and request.user.is_authenticated():
        user_ids.extend(Follow.objects.filter(user=request.user).values_list('object_id', flat=True))
    manufacturers = Product.valid_objects.filter(gender__in=[gender, 'U']) \
                                         .filter(likes__user__in=user_ids) \
                                         .values_list('manufacturer', 'manufacturer__name') \
                                         .annotate(Count('manufacturer')) \
                                         .order_by('-popularity', '-date_added')[:10]
    for manufacturer in manufacturers:
        popular_brands_in_network.append([manufacturer[0],
                                          manufacturer[1],
                                          Product.valid_objects.filter(gender__in=[gender, 'U'],
                                                                       manufacturer=manufacturer[0]) \
                                                               .order_by('-popularity', '-date_added')[:2]])

    response = render_to_response('apparel/brand_list.html', {
                'brands': brands,
                'popular_brands': popular_brands,
                'popular_brands_in_network': popular_brands_in_network,
                'next': request.get_full_path(),
                'APPAREL_GENDER': gender
            }, context_instance=RequestContext(request))
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)
    return response

def look_list(request, popular=None, search=None, contains=None, page=0, gender=None):
    """
    This view can list looks in four ways:

        1) If no argument is used a list of all looks is displayed.
        2) If popular-argument is set displays a list of all popular looks in your network.
        3) If search-argument is set displays a list of all matching looks to param 'q'.
        4) If contains-argument is set displays all looks that contains the product.

    """
    if not gender:
        gender = get_gender_from_cookie(request)

    if popular:
        if request.user.is_authenticated():
            queryset = get_top_looks_in_network(request.user)
        else:
            queryset = Look.objects.none()
    elif search:
        query_arguments = {'qf': 'text',
                           'defType': 'edismax',
                           'fq': 'django_ct:apparel.look',
                           'start': 0,
                           'rows': 500} # XXX: maximum search results, sync this with the count that is displayed in the search result box
        results = ApparelSearch(request.GET.get('q'), **query_arguments)
        queryset = Look.objects.filter(id__in=[doc.django_id for doc in results.get_docs()])
    elif contains:
        queryset = Look.objects.filter(id__in=LookComponent.objects.filter(product__slug=contains).values_list('look', flat=True))
    else:
        queryset = Look.objects.filter(likes__active=True, gender__in=[gender, 'U']).annotate(num_likes=Count('likes')).order_by('-num_likes').filter(num_likes__gt=0)

    if request.user.is_authenticated():
        user_ids = Follow.objects.filter(user=request.user).values_list('object_id', flat=True)
        most_looks_users = ApparelProfile.objects.annotate(look_count=Count('user__look')).order_by('-look_count').filter(look_count__gt=0, user__in=user_ids)
    else:
        most_looks_users = None

    latest_looks = Look.objects.filter(gender__in=[gender, 'U']).order_by('-created')[:16]
    paged_result, pagination = get_pagination_page(queryset, LOOK_PAGE_SIZE,
            request.GET.get('page', 1), 1, 2)

    if request.is_ajax():
        response = render_to_response('apparel/fragments/looks_middle_column.html', {
                    'pagination': pagination,
                    'current_page': paged_result,
                }, context_instance=RequestContext(request))
    else:
        response = render_to_response('apparel/look_list.html', {
                    'query': request.GET.get('q'),
                    'paginator': paged_result.paginator,
                    'pagination': pagination,
                    'current_page': paged_result,
                    'next': request.get_full_path(),
                    'most_looks_users': most_looks_users,
                    'latest_looks': latest_looks,
                    'APPAREL_GENDER': gender
                }, context_instance=RequestContext(request))
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)
    return response

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
                'object_url': request.build_absolute_uri(look.get_absolute_url())
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

    product_likes = Product.published_objects.filter(likes__user=request.user, likes__active=True).order_by('-likes__modified')

    context = RequestContext(request)

    data = {
        'object': form.instance,
        'form': form,
        'wardrobe': product_likes
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
        if request.is_ajax():
            return render_to_response('apparel/look_create_dialog.html', {'form': LookForm()}, context_instance=RequestContext(request))

        return render_to_response('apparel/look_create.html', {'form': LookForm()}, context_instance=RequestContext(request))

    if request.method == 'POST' and request.user.is_authenticated():
        form = LookForm(request.POST)

        if form.is_valid():
            look = form.save(commit=False)
            if request.POST.get('look_photo', None) or request.POST.get('look_photo_image.x', None):
                look.component = 'P'
            else:
                look.component = 'C'
            look.user = request.user
            look.save()

            if request.is_ajax():
                return HttpResponse(json.encode({'success': True, 'data': look}), mimetype='application/json')

            return HttpResponseRedirect(reverse('apparel.views.look_edit', args=(look.slug,)))

        return render_to_response('apparel/look_create.html', {'form': form}, context_instance=RequestContext(request))

    if request.is_ajax():
        return render_to_response('apparel/fragments/dialog_create_look.html', {}, context_instance=RequestContext(request))

    return render_to_response('apparel/look_create_unauthenticated.html', {}, context_instance=RequestContext(request))

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
            'tooltip_html': loader.render_to_string('apparel/fragments/look_product_tooltip.html', {'component': form.instance}, context_instance=RequestContext(request)),
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
    in_look = dict(map(lambda x: (x, components.filter(product__id=x).exists()), products))

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
        look.save()
        created = False
    else:
        look = Look(user=request.user, title=request.POST.get('new_name'), description='')
        look.save()
        created = True

    product = Product.objects.get(pk=request.POST.get('product'))
    added = True

    # If we add to a look, we should also added it to the "wardrobe" by liking
    product_like, _ = ProductLike.objects.get_or_create(user=request.user, product=product)
    product_like.active = True
    product_like.save()

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


def csrf_failure(request, reason=None):
    """
    Display error page for cross site forgery requests
    """
    if reason is None: reason = '[None given]'
    logging.debug("CSRF failure: %s" % reason)
    return render_to_response('403.html', { 'is_csrf': True, 'debug': settings.DEBUG, 'reason': reason }, context_instance=RequestContext(request))

def user_list(request, popular=None, gender=None, view_gender=[]):
    """
    Displays a list of profiles
    """
    if not gender:
        gender = get_gender_from_cookie(request)

    if view_gender and set(view_gender).issubset(set(['W', 'M'])):
        queryset = ApparelProfile.objects.select_related('user').filter(user__is_active=True, gender__in=view_gender)
    else:
        queryset = ApparelProfile.objects.select_related('user').filter(user__is_active=True)

    if popular:
        queryset = queryset.order_by('-followers_count', 'user__first_name', 'user__last_name', 'user__username')
    else:
        queryset = queryset.order_by('user__first_name', 'user__last_name', 'user__username')

    paged_result, pagination = get_pagination_page(queryset,
            10, request.GET.get('page', 1), 1, 2)

    # Latest active members
    latest_members = ApparelProfile.objects.select_related('user').filter(user__is_active=True).order_by('-user__date_joined')[:13]

    if request.is_ajax():
        response = render_to_response('apparel/fragments/user_list.html', {
                    'pagination': pagination,
                    'current_page': paged_result,
            }, context_instance=RequestContext(request))
    else:
        response = render_to_response('apparel/user_list.html', {
                'pagination': pagination,
                'current_page': paged_result,
                'next': request.get_full_path(),
                'facebook_friends': get_facebook_friends(request),
                'view_gender': view_gender[0] if len(view_gender) > 0 and view_gender[0] in ['W', 'M'] else 'A',
                'latest_members': latest_members,
                'APPAREL_GENDER': gender
            }, context_instance=RequestContext(request))
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)
    return response

def gender(request, view=None, gender=None):
    """
    Display gender selection front page, also handle change from one gender to the other.
    """
    if gender is not None:
        response = HttpResponseRedirect(request.GET.get('next', '/'))
        response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)
        return response

    if view is None:
        return HttpResponseNotFound()

    gender_cookie = get_gender_from_cookie(request)
    if gender_cookie == 'W':
        return HttpResponseRedirect(reverse('%s-women' % (view,)))
    elif gender_cookie == 'M':
        return HttpResponseRedirect(reverse('%s-men' % (view,)))

    # Set language to user's browser language for gender select view
    language = translation.get_language_from_request(request)
    translation.activate(language)
    request.LANGUAGE_CODE = translation.get_language()
    image = BackgroundImage.objects.get_random_image()

    return render_to_response('apparel/gender.html', {
            'men_url': reverse('%s-men' % (view,)),
            'women_url': reverse('%s-women' % (view,)),
            'next': request.GET.get('next', '/'),
            'image': str(image)
        }, context_instance=RequestContext(request))

def about(request):
    # Set language to user's browser language for gender select view
    language = translation.get_language_from_request(request)
    translation.activate(language)
    request.LANGUAGE_CODE = translation.get_language()
    image = BackgroundImage.objects.get_random_image()

    view = 'shop'

    return render_to_response('apparel/gender.html', {
            'men_url': reverse('%s-men' % (view,)),
            'women_url': reverse('%s-women' % (view,)),
            'next': request.GET.get('next', '/'),
            'image': str(image)
        }, context_instance=RequestContext(request))



def jobs(request):
    # Set language to user's browser language for gender select view
    language = translation.get_language_from_request(request)
    translation.activate(language)
    request.LANGUAGE_CODE = translation.get_language()
    image = BackgroundImage.objects.get_random_image()

    return render_to_response('apparel/jobs.html', {
            'image': str(image)
        }, context_instance=RequestContext(request))

@get_current_user
@login_required
def home(request, profile):
    """
    Displays the logged in user's page
    """
    # Update the time we last checked "friends updates"
    profile.updates_last_visit = datetime.datetime.now()
    queryset = profile.get_friend_updates()
    profile.save()

    # Retrieve most popular products in users network
    limit = 2
    user_ids = list(Follow.objects.filter(user=request.user).values_list('object_id', flat=True)) + [0]
    user_ids_or = ' OR '.join(str(x) for x in user_ids)


    # FIXME: Ugly solution, query solr for popular products, then query db for those two results, should be able to get this directly with db queries.
    query_arguments = {
        'sort': 'popularity desc',
        'start': 0,
        'rows': limit,
        'fq': [
            'django_ct:apparel.product',
            'user_likes:({0})'.format(user_ids_or),
            'availability:true',
            'published:true'
        ]
    }
    result = ApparelSearch('*:*', **query_arguments)
    popular_products = Product.objects.filter(id__in=[doc.django_id for doc in result.get_docs()])

    paged_result, pagination = get_pagination_page(queryset,
            FAVORITES_PAGE_SIZE, request.GET.get('page', 1), 1, 2)

    if request.is_ajax():
        return render_to_response('apparel/fragments/activity/list.html', {
            'pagination': pagination,
            'current_page': paged_result
        }, context_instance=RequestContext(request))

    return render_to_response('apparel/user_home.html', {
            'pagination': pagination,
            'current_page': paged_result,
            'next': request.get_full_path(),
            'profile': profile,
            'facebook_friends': get_facebook_friends(request),
            'popular_looks_in_network': get_top_looks_in_network(request.user, limit=limit),
            'popular_products_in_network': popular_products
        }, context_instance=RequestContext(request))

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

def index(request, gender=None):
    """
    NOT USED ANYMORE
    """
    ctx = {}
    ctx['pages'] = FirstPageContent.published_objects.filter(gender__in=['U', gender], language=request.LANGUAGE_CODE)
    ctx['popular_looks'] = get_top_looks(request, limit=8, gender=gender)
    ctx['all_colors'] = Option.objects.filter(option_type__name='color')
    # ctx['categories_all'] contains all categories, they will later be filtered
    ctx['categories_all'] = Category.objects.filter(on_front_page=True)
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

    arguments = {'defType': 'edismax',
                 'start': 0,
                 'rows': 1,
                 'fq': ['django_ct:apparel.product', 'availability:true', 'published:true', 'gender:(U OR %s)' % (gender)],
                 'qf': [],
                 'facet': 'on',
                 'facet.limit': -1,
                 'facet.mincount': 1,
                 'facet.field':  ['manufacturer_data', 'category']}

    facet_fields = ApparelSearch('*:*', **arguments).get_facet()['facet_fields']
    ctx['manufacturers'] = []
    for i, value in enumerate(facet_fields['manufacturer_data']):
        if i % 2 == 0:
            split = value.rsplit('|', 1)
            ctx['manufacturers'].append((int(split[1]), split[0]))

    # Get the categories to actually show
    category_ids = map(int, facet_fields['category'][::2])
    category_values = map(int, facet_fields['category'][1::2])
    ctx['categories'] = dict(zip(category_ids, category_values))

    ctx['APPAREL_GENDER'] = gender

    response = render_to_response('index.html', ctx, context_instance=RequestContext(request))
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)
    return response

def apparel_set_language(request):
    language = request.POST.get('language', None)
    if request.user.is_authenticated() and language is not None:
        profile = request.user.get_profile()
        profile.language = language
        profile.save()

    return set_language(request)

# Also update the language on the profile after a login, only works in django 1.3
# FIXME: update this code when django 1.3 is standard...
try:
    from django.contrib.auth.signals import user_logged_in

    def update_profile_language(sender, user, request, **kwargs):
        language = translation.get_language()
        if user.is_authenticated() and language is not None:
            profile = user.get_profile()
            profile.language = language
            profile.save()

    user_logged_in.connect(update_profile_language)

except ImportError:
    pass

#
# Utility routines. FIXME: Move these out
#

def get_top_looks(request, limit=10, gender=None):
    """
    Get the most popular looks, sorted by number of likes. If gender is set,
    also filter looks by gender.
    """
    if gender is not None:
        return Look.objects.filter(likes__active=True).filter(gender__in=['U', gender]).annotate(num_likes=CountPopularity('likes', field_two='apparel_look.created')).order_by('-num_likes').filter(num_likes__gt=0)[:limit]
    return Look.objects.filter(likes__active=True).annotate(num_likes=CountPopularity('likes', field_two='apparel_look.created')).order_by('-num_likes').filter(num_likes__gt=0)[:limit]

def get_most_followed_users(limit=2):
    #object_ids = [x['object_id'] for x in Follow.objects.values('object_id').annotate(Count('id')).order_by('-id__count')[:limit]]
    #return ApparelProfile.objects.select_related('user').filter(user__in=object_ids)
    # FIXME: This is inefficient because it creates a query for everyone object_id, better solution?
    apparel_profiles = []
    for object_id in Follow.objects.values_list('object_id', flat=True).annotate(count=Count('id')).order_by('-count')[:limit]:
        apparel_profiles.append(ApparelProfile.objects.select_related('user').get(user__id=object_id))
    return apparel_profiles

def get_top_looks_in_network(user, limit=None):
    content_type = ContentType.objects.get_for_model(User)
    user_ids = Follow.objects.filter(content_type=content_type, user=user).values_list('object_id', flat=True)
    looks = Look.objects.filter(Q(likes__active=True) & Q(user__in=user_ids)).annotate(num_likes=CountPopularity('likes', field_two='apparel_look.created')).order_by('-num_likes')

    if limit:
        return looks[:limit]

    return looks

def get_facebook_friends(request):
    facebook_user = get_facebook_user(request)
    if request.user.is_authenticated() and facebook_user:
        friends = facebook_user.graph.get_connections('me', 'friends')
        friends_uids = [f['id'] for f in friends['data']]
        return ApparelProfile.objects.filter(user__username__in=friends_uids)
