# -*- coding: utf-8 -*-
import logging
import re
import json
import datetime

from django.conf import settings
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponsePermanentRedirect, HttpResponseNotFound, Http404
from django.core.urlresolvers import reverse
from django.core.cache import cache
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
from django.utils.translation import ugettext_lazy as _
from hanssonlarsson.django.exporter import json as special_json
from sorl.thumbnail import get_thumbnail

from profile.models import ApparelProfile, Follow
from profile.utils import get_facebook_user
from apparel.decorators import seamless_request_handling
from apparel.decorators import get_current_user
from apparel.models import Brand, Product, ProductLike, Category, Option, VendorProduct, BackgroundImage
from apparel.models import Look, LookLike, LookComponent, ShortProductLink
from apparel.forms import LookForm, LookComponentForm
from apparel.search import ApparelSearch
from apparel.search import more_like_this_product
from apparel.utils import get_pagination_page, get_gender_from_cookie, CountPopularity, vendor_buy_url
from profile.notifications import process_like_look_created
from apparel.tasks import facebook_push_graph, facebook_pull_graph

from statistics.tasks import product_buy_click
from statistics.utils import get_client_referer, get_client_ip

FAVORITES_PAGE_SIZE = 30
LOOK_PAGE_SIZE = 6

#
# Redirects
#

def product_redirect(request, pk):
    """
    Makes it
    """
    product = get_object_or_404(Product, pk=pk, published=True)
    return HttpResponsePermanentRedirect(product.get_absolute_url())

def brand_redirect(request, pk):
    """
    Redirect from a brand id to brand profile page.
    """
    brand = get_object_or_404(Brand, pk=pk)
    return HttpResponsePermanentRedirect(brand.profile.get_absolute_url())

#
# Notifications
#

def notification_like_product(request):
    try:
        product_id = int(request.GET.get('id', None))
    except (ValueError, TypeError):
        return HttpResponseNotFound()

    product = get_object_or_404(Product, pk=product_id)
    url = request.build_absolute_uri(product.get_absolute_url())
    return render(request, 'apparel/notifications/like_product.html', {'object': product, 'url': url})

def notification_like_look(request):
    try:
        look_id = int(request.GET.get('id', None))
    except (ValueError, TypeError):
        return HttpResponseNotFound()

    look = get_object_or_404(Look, pk=look_id)
    url = request.build_absolute_uri(look.get_absolute_url())
    return render(request, 'apparel/notifications/like_look.html', {'object': look, 'url': url})

def notification_create_look(request):
    try:
        look_id = int(request.GET.get('id', None))
    except (ValueError, TypeError):
        return HttpResponseNotFound()

    look = get_object_or_404(Look, pk=look_id)
    url = request.build_absolute_uri(look.get_absolute_url())
    return render(request, 'apparel/notifications/create_look.html', {'object': look, 'url': url})

def notification_follow_member(request):
    try:
        profile_id = int(request.GET.get('id', None))
    except (ValueError, TypeError):
        return HttpResponseNotFound()

    profile = get_object_or_404(get_model('profile', 'ApparelProfile'), pk=profile_id)
    url = request.build_absolute_uri(profile.get_absolute_url())
    return render(request, 'apparel/notifications/follow_member.html', {'object': profile, 'url': url})

def notification_follow_brand(request):
    try:
        profile_id = int(request.GET.get('id', None))
    except (ValueError, TypeError):
        return HttpResponseNotFound()

    profile = get_object_or_404(get_model('profile', 'ApparelProfile'), pk=profile_id)
    url = request.build_absolute_uri(profile.get_absolute_url())
    return render(request, 'apparel/notifications/follow_brand.html', {'object': profile, 'url': url})

#
# Facebook calls
#


@login_required
def facebook_share(request, activity):
    action = request.POST.get('action', '')
    object_type = request.POST.get('object_type', '')
    object_url = request.POST.get('object_url', '')
    auto_share = request.POST.get('auto_share', '')

    if auto_share:
        share_settings = ['like_product', 'like_look', 'create_look', 'follow_profile']
        if auto_share in share_settings:
            profile = request.user.get_profile()
            setattr(profile, 'fb_share_%s' % (auto_share,), True)
            profile.save()

    facebook_user = get_facebook_user(request)
    if not facebook_user:
        return HttpResponse(json.dumps(dict(success=False, message='', error=_('Check your browser settings.').encode('utf-8'))), mimetype='application/json')

    if activity == 'push':
        facebook_push_graph.delay(request.user.pk, facebook_user.access_token, action, object_type, object_url)
    elif activity == 'pull':
        facebook_pull_graph.delay(request.user.pk, facebook_user.access_token, action, object_type, object_url)

    return HttpResponse(json.dumps(dict(success=True, message=_('Shared to your Facebook timeline!').encode('utf-8'), error='')), mimetype='application/json')

#
# Follow/Unfollow
#

@login_required
def follow_unfollow(request, profile_id, do_follow=True):
    """
    Either follows or unfollows a profile.
    """
    profile = ApparelProfile.objects.get(pk=profile_id)

    if request.user.get_profile() == profile:
        return HttpResponse(status=403)

    if do_follow:
        if request.user.get_profile().fb_share_follow_profile:
            facebook_user = get_facebook_user(request)
            if facebook_user:
                facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'follow', 'profile', request.build_absolute_uri(profile.get_absolute_url()))

        follow, _ = Follow.objects.get_or_create(user=request.user.get_profile(), user_follow=profile)
        if not follow.active:
            follow.active = True
            follow.save()

        return HttpResponse(status=201)

    follow, _ = Follow.objects.get_or_create(user=request.user.get_profile(), user_follow=profile)
    if follow.active:
        follow.active = False
        follow.save()

    facebook_user = get_facebook_user(request)
    if facebook_user:
        facebook_pull_graph.delay(request.user.pk, facebook_user.access_token, 'follow', 'profile', request.build_absolute_uri(profile.get_absolute_url()))

    return HttpResponse(status=204)

#
# Products
#

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
        user_looks = Look.published_objects.filter(user=request.user)
        is_in_wardrobe = ProductLike.objects.filter(user=request.user, product=product, active=True).exists()

    looks_with_product = Look.published_objects.filter(components__product=product).order_by('-modified')[:2]
    looks_with_product_count = Look.published_objects.filter(components__product=product).aggregate(Count('id')).get('id__count', 0)

    # Comments
    content_type = ContentType.objects.get_for_model(Product)
    comments =  Comment.objects.filter(content_type=content_type, object_pk=product.pk, is_public=True, is_removed=False).select_related('user', 'user__profile')

    # Likes
    likes = product.likes.filter(active=True).order_by('-modified').select_related('user', 'user__profile')
    regular_likes = likes.filter(user__profile__blog_url=None)
    partner_likes = likes.exclude(user__profile__blog_url=None)

    # Full image url
    try:
        product_full_image = request.build_absolute_uri(get_thumbnail(product.product_image, '328', upscale=False, crop='noop').url)
    except IOError:
        logging.error('Product id %s does not have a valid image on disk' % (product.pk,))
        raise Http404

    # Full brand url
    product_brand_full_url = ''
    if product.manufacturer and product.manufacturer.profile:
        product_brand_full_url = request.build_absolute_uri(product.manufacturer.profile.get_absolute_url())

    # Partner user
    product_short_link = None
    if request.user.is_authenticated() and request.user.get_profile().is_partner:
        try:
            partner_short = ShortProductLink.objects.get(product=product, user=request.user)
            product_short_link = reverse('product-short-link', args=[partner_short.link()])
            product_short_link = request.build_absolute_uri(product_short_link)
        except ShortProductLink.DoesNotExist:
            pass

    # More like this body
    mlt_body = '%s %s %s %s' % (product.product_name, product.manufacturer.name, ', '.join(product.colors), ', '.join([x.name for x in product.categories]))

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
                'more_like_this': more_like_this_product(mlt_body, product.gender, 20),
                'comments': comments,
                'product_full_url': request.build_absolute_uri(product.get_absolute_url()),
                'product_full_image': product_full_image,
                'product_brand_full_url': product_brand_full_url,
                'likes': regular_likes,
                'partner_likes': partner_likes,
                'product_short_link': product_short_link,
            }, context_instance=RequestContext(request),
        )


def product_generate_short_link(request, slug):
    """
    Generate a short product link and return it in a JSON response.
    """
    if not request.user.is_authenticated() or not request.user.get_profile().is_partner:
        raise Http404

    product = get_object_or_404(Product, slug=slug, published=True)
    product_short_link, created = ShortProductLink.objects.get_or_create(product=product, user=request.user)
    product_short_link = reverse('product-short-link', args=[product_short_link.link()])
    product_short_link = request.build_absolute_uri(product_short_link)

    return render(request, 'apparel/fragments/product_short_link.html', {'product_short_link': product_short_link})


def product_short_link(request, short_link):
    """
    Takes a short product link and redirect to buy url.
    """
    try:
        short_product = ShortProductLink.objects.get_for_short_link(short_link)
    except ShortProductLink.DoesNotExist:
        raise Http404

    product_buy_click.delay(short_product.product.pk, get_client_referer(request), get_client_ip(request), short_product.user_id, 'Ext-Link')

    return HttpResponseRedirect(vendor_buy_url(short_product.product.pk,
                                               short_product.product.default_vendor,
                                               short_product.user_id,
                                               'Ext-Link'))


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

    return _product_like(request, product, action)

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

    return _product_like(request, product, action)

def _product_like(request, product, action):
    if action == 'like':
        if request.user.get_profile().fb_share_like_product:
            facebook_user = get_facebook_user(request)
            if facebook_user:
                facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'like', 'object', request.build_absolute_uri(product.get_absolute_url()))
    elif action == 'unlike':
        facebook_user = get_facebook_user(request)
        if facebook_user:
            facebook_pull_graph.delay(request.user.pk, facebook_user.access_token, 'like', 'object', request.build_absolute_uri(product.get_absolute_url()))

    default_active = True if action == 'like' else False
    product_like, created = ProductLike.objects.get_or_create(user=request.user, product=product, defaults={'active': default_active})
    if not created:
        product_like.active = default_active
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

    if action == 'like':
        if request.user.get_profile().fb_share_like_look:
            facebook_user = get_facebook_user(request)
            if facebook_user:
                facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'like', 'object', request.build_absolute_uri(look.get_absolute_url()))
    elif action == 'unlike':
        facebook_user = get_facebook_user(request)
        if facebook_user:
            facebook_pull_graph.delay(request.user.pk, facebook_user.access_token, 'like', 'object', request.build_absolute_uri(look.get_absolute_url()))

    default_active = True if action == 'like' else False
    look_like, created = LookLike.objects.get_or_create(user=request.user, look=look, defaults={'active': default_active})
    if not created:
        look_like.active = default_active
        look_like.save()

    if action == 'like':
        process_like_look_created.delay(look.user, request.user, look_like)

    return HttpResponse(json.dumps(dict(success=True, error_message=None)), mimetype='application/json')

def brand_list(request, gender=None, popular=False):
    """
    List all brands.
    """
    if not gender:
        gender = get_gender_from_cookie(request)

    # Most popular brand pages
    popular_brands = ApparelProfile.objects.filter(user__is_active=True, is_brand=True).order_by('-followers_count')[:10]

    # Most popular products
    user_ids = []
    if request.user and request.user.is_authenticated():
        user_ids.extend(Follow.objects.filter(user=request.user.get_profile(), active=True).values_list('user_follow__user_id', flat=True))
    popular_products = Product.valid_objects.distinct().filter(likes__user__in=user_ids).order_by('-popularity')[:10]

    response = render_to_response('apparel/brand_list.html', {
                'popular_brands': popular_brands,
                'popular_products': popular_products,
                'popular': popular,
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
            queryset = get_top_looks_in_network(request.user.get_profile())
        else:
            queryset = Look.objects.none()
    elif search:
        if not gender:
            gender_field = 'gender:(U OR M OR W)'
        else:
            gender_field = 'gender:(U OR %s)' % (gender,)
        query_arguments = {'qf': 'text',
                           'defType': 'edismax',
                           'fq': ['django_ct:apparel.look', gender_field],
                           'start': 0,
                           'rows': 500} # XXX: maximum search results, sync this with the count that is displayed in the search result box
        results = ApparelSearch(request.GET.get('q'), **query_arguments)
        queryset = Look.published_objects.filter(id__in=[doc.django_id for doc in results.get_docs()])
    elif contains:
        queryset = Look.published_objects.filter(id__in=LookComponent.objects.filter(product__slug=contains).values_list('look', flat=True))
    else:
        queryset = Look.published_objects.filter(gender__in=[gender, 'U']).order_by('-popularity')

    paged_result, pagination = get_pagination_page(queryset, LOOK_PAGE_SIZE,
            request.GET.get('page', 1), 1, 2)

    if request.is_ajax():
        response = render_to_response('apparel/fragments/looks_medium.html', {
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
                    'APPAREL_GENDER': gender
                }, context_instance=RequestContext(request))
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)
    return response

def look_detail(request, slug):
    look = get_object_or_404(Look, slug=slug)

    # Only show unpublished looks to creator
    if not look.published and look.user != request.user:
        raise Http404()

    looks_by_user = Look.published_objects.filter(user=look.user).exclude(pk=look.id).order_by('-modified')[:8]

    look_saved = False
    if 'look_saved' in request.session:
        if request.user.get_profile().fb_share_create_look:
            if look.display_components.count() > 0:
                facebook_user = get_facebook_user(request)
                if facebook_user:
                    facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'create', 'look', request.build_absolute_uri(look.get_absolute_url()))
        else:
            look_saved = request.session['look_saved']

        del request.session['look_saved']

    # Likes
    likes = look.likes.filter(active=True).order_by('-modified').select_related('user', 'user__profile')

    # Base url
    base_url = request.build_absolute_uri('/')[:-1]

    return render_to_response(
            'apparel/look_detail.html',
            {
                'object': look,
                'looks_by_user': looks_by_user,
                'tooltips': True,
                'object_url': request.build_absolute_uri(look.get_absolute_url()),
                'look_full_image': request.build_absolute_uri(look.static_image.url),
                'look_saved': look_saved,
                'likes': likes,
                'base_url': base_url
            },
            context_instance=RequestContext(request),
        )

def look_embed(request, slug):
    look = get_object_or_404(Look, slug=slug)
    base_url = request.build_absolute_uri('/')[:-1]

    return render(request, 'apparel/look_embed.html', {'object': look, 'base_url': base_url})


@login_required
@seamless_request_handling
def look_delete(request, slug):
    look = get_object_or_404(Look, slug=slug, user=request.user)
    if look:
        # pull create look activity from facebook (cannot be in a pre_delete signal because request object requirement)
        facebook_user = get_facebook_user(request)
        if facebook_user:
            facebook_pull_graph.delay(request.user.pk, facebook_user.access_token, 'create', 'look', request.build_absolute_uri(look.get_absolute_url()))

        look.delete()
        return (True, HttpResponseRedirect(reverse('profile.views.looks', args=(request.user.get_profile().slug,))))
    else:
        return (False, HttpResponseRedirect(reverse('profile.views.looks', args=(request.user.get_profile().slug,))))

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

    queryset = ApparelProfile.objects.select_related('user').filter(user__is_active=True, is_brand=False)

    if view_gender and set(view_gender).issubset(set(['W', 'M'])):
        queryset = queryset.filter(gender__in=view_gender)

    if popular:
        queryset = queryset.order_by('-followers_count', 'user__first_name', 'user__last_name', 'user__username')
    else:
        queryset = queryset.order_by('user__first_name', 'user__last_name', 'user__username')

    paged_result, pagination = get_pagination_page(queryset,
            10, request.GET.get('page', 1), 1, 2)

    # Latest active members
    latest_members = ApparelProfile.objects.select_related('user').filter(user__is_active=True, is_brand=False).order_by('-user__date_joined')[:13]

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
                'view_gender': view_gender[0] if len(view_gender) > 0 and view_gender[0] in ['W', 'M'] else 'A',
                'latest_members': latest_members,
                'APPAREL_GENDER': gender
            }, context_instance=RequestContext(request))
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)
    return response

def change_gender(request, *args, **kwargs):
    """
    Handle change from one gender to the other.
    """
    current_gender = gender = get_gender_from_cookie(request)
    if request.method == 'POST':
        gender = request.POST.get('gender', 'W')

    next_url = request.REQUEST.get('next', None)
    if not next_url:
        next_url = request.META.get('HTTP_REFERER', None)
        if not next_url:
            next_url = '/'

    if current_gender != gender:
        next_url_parts = next_url.split('/')
        if next_url_parts[-2] == 'women':
            next_url_parts[-2] = 'men'
        elif next_url_parts[-2] == 'men':
            next_url_parts[-2] = 'women'
        next_url = '/'.join(next_url_parts)

    response = HttpResponseRedirect(next_url)
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)

    return response

def gender(request, *args, **kwargs):#view=None, gender=None):
    """
    Display gender selection front page, also handle change from one gender to the other.
    """
    gender = kwargs.get('gender')
    view = kwargs.get('view')

    if gender is not None:
        response = HttpResponseRedirect(request.GET.get('next', '/'))
        response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)
        return response

    if view is None:
        return HttpResponseNotFound()

    gender_cookie = get_gender_from_cookie(request)
    if gender_cookie == 'W':
        return HttpResponseRedirect(reverse('%s-women' % (view,), args=args))
    elif gender_cookie == 'M':
        return HttpResponseRedirect(reverse('%s-men' % (view,), args=args))

    return HttpResponseRedirect(reverse('%s-women' % (view,), args=args))

def about(request):
    return render_to_response('apparel/about.html', {}, context_instance=RequestContext(request))

def jobs(request):
    # Set language to user's browser language for gender select view
    language = translation.get_language_from_request(request)
    translation.activate(language)
    request.LANGUAGE_CODE = translation.get_language()
    image = BackgroundImage.objects.get_random_image()

    return render_to_response('apparel/jobs.html', {
            'image': str(image)
        }, context_instance=RequestContext(request))


def apparel_set_language(request):
    language = request.POST.get('language', translation.get_language())
    if request.user.is_authenticated():
        profile = request.user.get_profile()
        profile.language = language
        profile.save()

    return set_language(request)


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
    brand = 0
    try:
        brand = int(request.GET.get('brand', 0))
    except ValueError:
        pass

    return render_to_response('apparel/fragments/dialog_follow_user.html',
            {'next': request.GET.get('next', '/'),
             'brand': brand}, context_instance=RequestContext(request))

def facebook_friends_widget(request):
    """
    Return html template with facebook friends on apprl. Only works through an
    ajax request.
    """
    if not request.is_ajax():
        raise Http404

    fids = []
    try:
        fids = map(int, request.POST.get('fids', '').split(','))
    except ValueError:
        pass

    if not fids:
        return HttpResponse('')

    friends = ApparelProfile.objects.filter(user__username__in=fids)

    return render_to_response('apparel/fragments/facebook_friends.html', {
            'facebook_friends': friends,
        }, context_instance=RequestContext(request))

#
# Utility routines. FIXME: Move these out
#

def get_top_looks_in_network(profile, limit=None):
    user_ids = Follow.objects.filter(user=profile, active=True).values_list('user_follow__user', flat=True)
    # TODO: add active/published flag here later
    looks = Look.published_objects.distinct().filter(user__in=user_ids).order_by('-popularity', '-created')

    if limit:
        return looks[:limit]

    return looks

def get_top_products_in_network(profile, limit=None):
    user_ids = Follow.objects.filter(user=profile, active=True).values_list('user_follow__user', flat=True)
    products = Product.valid_objects.distinct().filter(likes__active=True, likes__user__in=user_ids).order_by('-popularity')

    if limit:
        return products[:limit]

    return products
