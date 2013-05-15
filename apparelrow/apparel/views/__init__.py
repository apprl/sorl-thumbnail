# -*- coding: utf-8 -*-
import logging
import re
import json
import datetime
import os.path

from django.conf import settings
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponsePermanentRedirect, HttpResponseNotFound, Http404
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db.models import Q, Max, Min, Count, Sum, connection, signals, get_model
from django.template import RequestContext, loader
from django.template.loader import get_template
from django.template.defaultfilters import floatformat
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.views.i18n import set_language
from django.views.decorators.http import require_POST
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from sorl.thumbnail import get_thumbnail

from apparelrow.profile.models import Follow
from apparelrow.profile.utils import get_facebook_user
from apparelrow.profile.notifications import process_like_look_created

from apparelrow.apparel.decorators import seamless_request_handling
from apparelrow.apparel.models import Brand, Product, ProductLike, Category, Option, VendorProduct, BackgroundImage
from apparelrow.apparel.models import Look, LookLike, LookComponent, ShortProductLink
from apparelrow.apparel.forms import LookForm, LookComponentForm
from apparelrow.apparel.search import ApparelSearch
from apparelrow.apparel.search import more_like_this_product
from apparelrow.apparel.utils import get_pagination_page, get_gender_from_cookie, CountPopularity, vendor_buy_url, get_product_alternative
from apparelrow.apparel.tasks import facebook_push_graph, facebook_pull_graph, look_popularity

from apparelrow.statistics.tasks import product_buy_click
from apparelrow.statistics.utils import get_client_referer, get_client_ip, get_user_agent

FAVORITES_PAGE_SIZE = 30
LOOK_PAGE_SIZE = 6

#
# Sitemap
#

def sitemap_view(request, section):
    path = os.path.join(settings.PROJECT_ROOT, 'sitemaps', 'sitemap-%s.xml.gz' % (section,))
    if not os.path.exists(path):
        raise Http404()

    f = open(path)
    content = f.readlines()
    f.close()
    return HttpResponse(content, mimetype='application/xml')


#
# Redirects
#

def product_redirect_by_id(request, pk):
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
    return HttpResponsePermanentRedirect(brand.user.get_absolute_url())

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

    profile = get_object_or_404(get_user_model(), pk=profile_id)
    url = request.build_absolute_uri(profile.get_absolute_url())
    return render(request, 'apparel/notifications/follow_member.html', {'object': profile, 'url': url})

def notification_follow_brand(request):
    try:
        profile_id = int(request.GET.get('id', None))
    except (ValueError, TypeError):
        return HttpResponseNotFound()

    profile = get_object_or_404(get_user_model(), pk=profile_id)
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
            setattr(request.user, 'fb_share_%s' % (auto_share,), True)
            request.user.save()

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
    profile = get_user_model().objects.get(pk=profile_id)

    if request.user == profile:
        return HttpResponse(status=403)

    if do_follow:
        if request.user.fb_share_follow_profile:
            facebook_user = get_facebook_user(request)
            if facebook_user:
                facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'follow', 'profile', request.build_absolute_uri(profile.get_absolute_url()))

        follow, _ = Follow.objects.get_or_create(user=request.user, user_follow=profile)
        if not follow.active:
            follow.active = True
            follow.save()

        return HttpResponse(status=201)

    follow, _ = Follow.objects.get_or_create(user=request.user, user_follow=profile)
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

    is_in_wardrobe = False
    user_looks = []
    if request.user.is_authenticated():
        user_looks = Look.published_objects.filter(user=request.user)
        is_in_wardrobe = ProductLike.objects.filter(user=request.user, product=product, active=True).exists()

    looks_with_product = Look.published_objects.filter(components__product=product).distinct().order_by('-modified')[:2]
    looks_with_product_count = Look.published_objects.filter(components__product=product).distinct().count()

    # Comments
    content_type = ContentType.objects.get_for_model(Product)
    comments =  Comment.objects.filter(content_type=content_type, object_pk=product.pk, is_public=True, is_removed=False).select_related('user')

    # Likes
    likes = product.likes.filter(active=True).order_by('modified').select_related('user')
    regular_likes = likes.filter(Q(user__blog_url__isnull=True) | Q(user__blog_url__exact=''))
    partner_likes = likes.exclude(Q(user__blog_url__isnull=True) | Q(user__blog_url__exact=''))

    # Full image url
    try:
        product_full_image = request.build_absolute_uri(get_thumbnail(product.product_image, '328', upscale=False, crop='noop').url)
    except IOError:
        logging.error('Product id %s does not have a valid image on disk' % (product.pk,))
        raise Http404

    # Full brand url
    product_brand_full_url = ''
    if product.manufacturer and product.manufacturer.user:
        product_brand_full_url = request.build_absolute_uri(product.manufacturer.user.get_absolute_url())

    # Partner user
    product_short_link = None
    if request.user.is_authenticated() and request.user.is_partner:
        try:
            partner_short = ShortProductLink.objects.get(product=product, user=request.user)
            product_short_link = reverse('product-short-link', args=[partner_short.link()])
            product_short_link = request.build_absolute_uri(product_short_link)
        except ShortProductLink.DoesNotExist:
            pass

    # More like this body
    mlt_body = '%s %s %s %s' % (product.product_name, product.manufacturer.name, ', '.join(product.colors), ', '.join([x.name for x in product.categories]))

    # More alternatives
    alternative = get_product_alternative(product)

    # Referral SID
    referral_sid = request.GET.get('sid', 0)
    try:
        sid = int(referral_sid)
    except (TypeError, ValueError, AttributeError):
        sid = 0

    return render_to_response(
            'apparel/product_detail.html',
            {
                'object': product,
                'user_looks': user_looks,
                'is_in_wardrobe': is_in_wardrobe,
                'looks_with_product': looks_with_product,
                'looks_with_product_count': looks_with_product_count,
                'object_url': request.build_absolute_uri(),
                'more_like_this': more_like_this_product(mlt_body, product.gender, 20),
                'comments': comments,
                'product_full_url': request.build_absolute_uri(product.get_absolute_url()),
                'product_full_image': product_full_image,
                'product_brand_full_url': product_brand_full_url,
                'likes': regular_likes,
                'partner_likes': partner_likes,
                'product_short_link': product_short_link,
                'referral_sid': referral_sid,
                'alternative': alternative,
            }, context_instance=RequestContext(request),
        )


def product_generate_short_link(request, slug):
    """
    Generate a short product link and return it in a JSON response.
    """
    if not request.user.is_authenticated() or not request.user.is_partner:
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

    return HttpResponsePermanentRedirect(reverse('product-redirect', args=(short_product.product_id, 'Ext-Link', short_product.user_id)))


def product_redirect(request, pk, page='Default', sid=0):
    """
    Display a html redirect page for product pk and page/sid combo.
    """
    product = get_object_or_404(Product, pk=pk, published=True)

    url = vendor_buy_url(pk, product.default_vendor, sid, page)
    data = {'id': product.pk,
            'redirect_url': url,
            'store': product.default_vendor.vendor.name,
            'price': floatformat(product.default_vendor.lowest_price_in_sek, 0),
            'slug': product.slug,
            'page': page,
            'sid': sid}

    return render(request, 'redirect.html', data)


@require_POST
def product_track(request, pk, page='Default', sid=0):
    """
    Fires a product_buy_click task when called.
    """
    product_buy_click.delay(pk, '%s\n%s' % (request.POST.get('referer', ''), get_client_referer(request)), get_client_ip(request), get_user_agent(request), sid, page)

    return HttpResponse()


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
    except (Product.MultipleObjectsReturned, Product.DoesNotExist) as e:
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
    except (Product.MultipleObjectsReturned, Product.DoesNotExist) as e:
        return HttpResponse(json.dumps(dict(success=False, error_message='No product found')), mimetype='application/json')

    return _product_like(request, product, action)

def _product_like(request, product, action):
    if action == 'like':
        if request.user.fb_share_like_product:
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
    except (Look.MultipleObjectsReturned, Look.DoesNotExist) as e:
        return HttpResponse(json.dumps(dict(success=False, error_message='No look found')), mimetype='application/json')

    if action == 'like':
        if request.user.fb_share_like_look:
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

    look_popularity.delay(look)

    return HttpResponse(json.dumps(dict(success=True, error_message=None)), mimetype='application/json')

def brand_list(request, gender=None):
    """
    List all brands.
    """
    if not gender:
        gender = get_gender_from_cookie(request)

    # Most popular brand pages
    # Using a raw query to annotate the popular brand profile list with is_following
    if request.user.is_authenticated():
        popular_brands = get_user_model().objects.raw('SELECT pu.*, pf.id AS is_following FROM profile_user pu LEFT OUTER JOIN profile_follow pf ON pf.user_follow_id = pu.id AND pf.user_id = %s WHERE pu.is_brand = true AND pu.is_active = true ORDER BY pu.followers_count DESC LIMIT 20', [request.user.pk])
    else:
        popular_brands = get_user_model().objects.raw('SELECT *, false AS is_following FROM profile_user WHERE is_brand = true AND is_active = true ORDER BY followers_count DESC LIMIT 20')

    # Most popular products
    popular_products = None
    if request.user.is_authenticated():
        follows = Follow.objects.filter(user=request.user, active=True).values('user_follow_id')
        popular_products = Product.valid_objects.distinct() \
                                                .filter(likes__user__in=follows) \
                                                .order_by('-popularity') \
                                                .select_related('manufacturer')[:10]

    response = render_to_response('apparel/brand_list.html', {
                'popular_brands': popular_brands,
                'popular_products': popular_products,
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
        queryset = Look.published_objects.filter(components__product__slug=contains).distinct()
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
    look = get_object_or_404(get_model('apparel', 'Look'), slug=slug)

    # Only show unpublished looks to creator
    if not look.published and look.user != request.user:
        raise Http404()

    looks_by_user = Look.published_objects.filter(user=look.user).exclude(pk=look.id).order_by('-modified')[:8]

    look_created = False
    if 'look_created' in request.session:
        look_created = request.session['look_created']
        del request.session['look_created']

    look_saved = False
    if 'look_saved' in request.session:
        if request.user.fb_share_create_look:
            if look.display_components.count() > 0:
                facebook_user = get_facebook_user(request)
                if facebook_user:
                    facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'create', 'look', request.build_absolute_uri(look.get_absolute_url()))
        else:
            look_saved = request.session['look_saved']

        del request.session['look_saved']

    # Likes
    likes = look.likes.filter(active=True).order_by('-modified').select_related('user')

    # Base url
    base_url = request.build_absolute_uri('/')[:-1]

    # Components
    if look.display_with_component == 'C':
        components = look.collage_components.select_related('product')
    elif look.display_with_component == 'P':
        components = look.photo_components.select_related('product')

    for component in components:
        component.style_embed = component._style(min(694, look.image_width) / float(look.width))

    return render_to_response(
            'apparel/look_detail.html',
            {
                'object': look,
                'components': components,
                'looks_by_user': looks_by_user,
                'tooltips': True,
                'object_url': request.build_absolute_uri(look.get_absolute_url()),
                'look_full_image': request.build_absolute_uri(look.static_image.url),
                'look_saved': look_saved,
                'look_created': look_created,
                'likes': likes,
                'base_url': base_url
            },
            context_instance=RequestContext(request),
        )


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
        return (True, HttpResponseRedirect(reverse('profile-looks', args=(request.user.slug,))))
    else:
        return (False, HttpResponseRedirect(reverse('profile-looks', args=(request.user.slug,))))


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

    queryset = get_user_model().objects.filter(is_active=True, is_brand=False)

    if view_gender and set(view_gender).issubset(set(['W', 'M'])):
        queryset = queryset.filter(gender__in=view_gender)

    if popular:
        queryset = queryset.order_by('-popularity', '-followers_count', 'first_name', 'last_name', 'username')
    else:
        queryset = queryset.order_by('first_name', 'last_name', 'username')

    paged_result, pagination = get_pagination_page(queryset,
            10, request.GET.get('page', 1), 1, 2)

    # Latest active members
    latest_members = get_user_model().objects.filter(is_active=True, is_brand=False).order_by('-date_joined')[:13]

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
        request.user.language = language
        request.user.save()

    return set_language(request)


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

def dialog_create_look(request):
    """
    Dialog create look for unauthenticated users.
    """
    return render_to_response('apparel/fragments/dialog_create_look.html',
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

    friends = get_user_model().objects.filter(username__in=fids)

    return render_to_response('apparel/fragments/facebook_friends.html', {
            'facebook_friends': friends,
        }, context_instance=RequestContext(request))

#
# Utility routines. FIXME: Move these out
#

def get_top_looks_in_network(profile, limit=None):
    user_ids = Follow.objects.filter(user=profile, active=True).values_list('user_follow', flat=True)
    # TODO: add active/published flag here later
    looks = Look.published_objects.distinct().filter(user__in=user_ids).order_by('-popularity', '-created')

    if limit:
        return looks[:limit]

    return looks

def get_top_products_in_network(profile, limit=None):
    user_ids = Follow.objects.filter(user=profile, active=True).values_list('user_follow', flat=True)
    products = Product.valid_objects.distinct().filter(likes__active=True, likes__user__in=user_ids).order_by('-popularity')

    if limit:
        return products[:limit]

    return products
