# -*- coding: utf-8 -*-
import logging
import json
import datetime
from apparelrow.profile.models import NotificationEvent
from django.http.response import HttpResponseNotAllowed
import os.path
import string
import urllib
import urlparse
from apparelrow.apparel.utils import currency_exchange
import decimal
import re
import tldextract

from solrq import Q as SQ
from django.conf import settings
from django.shortcuts import render, render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponsePermanentRedirect, HttpResponseNotFound, Http404
from django.core.urlresolvers import reverse
from django.db.models import Q, Count, get_model
from django.template import RequestContext, loader
from django.template.loader import render_to_string
from django.template.defaultfilters import floatformat
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic.base import RedirectView
from django.utils import translation, timezone
from django.utils.encoding import smart_unicode, smart_str
from django.utils.translation import ugettext_lazy as _
from sorl.thumbnail import get_thumbnail

from localeurl.views import change_locale

from apparelrow.profile.models import Follow
from apparelrow.profile.utils import get_facebook_user
from apparelrow.profile.notifications import process_like_look_created

from apparelrow.apparel.middleware import REFERRAL_COOKIE_NAME
from apparelrow.apparel.decorators import seamless_request_handling
from apparelrow.apparel.models import Brand, Product, ProductLike
from apparelrow.apparel.models import Look, LookLike, ShortProductLink, ShortStoreLink, ShortDomainLink
from apparelrow.apparel.models import get_cuts_for_user_and_vendor
from apparelrow.apparel.search import ApparelSearch, more_like_this_product, more_alternatives
from apparelrow.apparel.utils import get_paged_result, vendor_buy_url, get_featured_activity_today, \
    select_from_multi_gender, JSONResponse, JSONPResponse
from apparelrow.apparel.tasks import facebook_push_graph, facebook_pull_graph, look_popularity, build_static_look_image

from apparelrow.activity_feed.views import user_feed

from apparelrow.statistics.tasks import product_buy_click
from apparelrow.statistics.utils import get_client_referer, get_client_ip, get_user_agent
from pysolr import Solr

logger = logging.getLogger("apparelrow")

FAVORITES_PAGE_SIZE = 30
LOOK_PAGE_SIZE = 12


class BrandRedirectView(RedirectView):
    permanent = False
    query_string = True

    def get_redirect_url(self, slug=None, gender=None):
        if slug is not None:
            if gender is not None:
                return '%s?gender=%s' % (reverse('brand-likes', args=(slug,)), gender)

            return reverse('brand-likes', args=(slug,))

        return reverse('brand-likes')


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


def notifications_seen_all(request):
    if request.method == 'POST' and request.is_ajax():
        user_id = request.POST.get('user_id', None)
        queryset = get_model('profile', 'NotificationEvent').objects.filter(owner_id=user_id)
        for notificationevent in queryset:
            notificationevent.seen = True
            notificationevent.save()
        return HttpResponse()
    else:
        return HttpResponseNotAllowed("Only POST requests allowed")


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
        return HttpResponse(
            json.dumps(dict(success=False, message='', error=_('Check your browser settings.').encode('utf-8'))),
            mimetype='application/json')

    if activity == 'push':
        facebook_push_graph.delay(request.user.pk, facebook_user.access_token, action, object_type, object_url)
    elif activity == 'pull':
        facebook_pull_graph.delay(request.user.pk, facebook_user.access_token, action, object_type, object_url)

    return HttpResponse(
        json.dumps(dict(success=True, message=_('Shared to your Facebook timeline!').encode('utf-8'), error='')),
        mimetype='application/json')


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
                facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'follow', 'profile',
                                          request.build_absolute_uri(profile.get_absolute_url()))

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
        facebook_pull_graph.delay(request.user.pk, facebook_user.access_token, 'follow', 'profile',
                                  request.build_absolute_uri(profile.get_absolute_url()))

    return HttpResponse(status=204)


#
# Store short link
#

def store_short_link(request, short_link, user_id=None):
    """
    Takes a short short link and redirect to associated url.
    """
    try:
        url, name = ShortStoreLink.objects.get_for_short_link(short_link, user_id)
    except ShortStoreLink.DoesNotExist:
        raise Http404

    if user_id is None:
        user_id = 0

    return render(request, 'redirect_no_product.html',
                  {'redirect_url': url, 'name': name, 'user_id': user_id, 'page': 'Ext-Store',
                   'event': 'StoreLinkClick'})


#
# Products
#

def get_product_from_slug(slug, **kwargs):
    try:
        product = Product.objects.get(slug=slug, **kwargs)
    except Product.MultipleObjectsReturned:
        products = Product.objects.filter(slug=slug, **kwargs)
        counter = 0
        for item in products:
            item_saved = False
            while not item_saved:
                slug = "%s-%s" % (item.slug, counter)
                counter += 1
                if not Product.objects.filter(slug=slug).exists():
                    item.slug = slug
                    item.save()
                    item_saved = True
        product = products[0]
    except Product.DoesNotExist:
        raise Http404("No Product matches the given query.")
    return product


def product_detail(request, slug):
    kwargs = {'published': True, 'gender__isnull': False}
    product = get_product_from_slug(slug, **kwargs)

    is_liked = False
    if request.user.is_authenticated():
        is_liked = ProductLike.objects.filter(user=request.user, product=product, active=True).exists()

    looks_with_product = Look.published_objects.filter(user__is_hidden=False,
                                                       components__product=product).distinct().order_by('-modified')[:2]
    looks_with_product_count = Look.published_objects.filter(user__is_hidden=False,
                                                             components__product=product).distinct().count()

    # Likes
    likes = product.likes.filter(active=True, user__is_hidden=False).order_by('modified').select_related('user')
    regular_likes = likes.filter(Q(user__blog_url__isnull=True) | Q(user__blog_url__exact=''))
    partner_likes = likes.exclude(Q(user__blog_url__isnull=True) | Q(user__blog_url__exact=''))

    # Full image url
    try:
        product_full_image = request.build_absolute_uri(
            get_thumbnail(product.product_image, '328', upscale=False, crop='noop').url)
    except IOError:
        logging.error('Product id %s does not have a valid image on disk' % (product.pk,))
        raise Http404

    # Full brand url
    product_brand_full_url = ''
    if product.manufacturer and product.manufacturer.user:
        product_brand_full_url = request.build_absolute_uri(product.manufacturer.user.get_absolute_url())

    # More like this body
    mlt_body = '%s %s %s %s' % (product.product_name, product.manufacturer.name, ', '.join(product.colors),
                                ', '.join([x.name for x in product.categories]))

    # More alternatives
    # alternative = get_product_alternative(product)
    alternative, alternative_url = more_alternatives(product, request.session.get('location', 'ALL'), 9)

    # Referral SID
    referral_sid = request.GET.get('sid', 0)
    try:
        sid = int(referral_sid)
    except (TypeError, ValueError, AttributeError):
        sid = 0

    # Get the store commission
    earning_cut = product.get_product_earning(request.user)

    # Cost per click
    default_vendor = product.default_vendor
    cost_per_click = 0
    if default_vendor and default_vendor.vendor.is_cpc:
        user, cut, referral_cut, publisher_cut = get_cuts_for_user_and_vendor(request.user.id, default_vendor.vendor)
        click_cut = cut * publisher_cut
        earning_cut = click_cut
        try:
            cost_per_click = get_model('dashboard', 'ClickCost').objects.get(vendor=default_vendor.vendor)
        except get_model('dashboard', 'ClickCost').DoesNotExist:
            logger.warning("ClickCost not defined for default vendor %s of the product %s" % (
                product.default_vendor, product.product_name))

    return render_to_response(
        'apparel/product_detail.html',
        {
            'object': product,
            'is_liked': is_liked,
            'looks_with_product': looks_with_product,
            'looks_with_product_count': looks_with_product_count,
            'object_url': request.build_absolute_uri(),
            'more_like_this': more_like_this_product(mlt_body, product.gender, request.session.get('location', 'ALL'),
                                                     9),
            'product_full_url': request.build_absolute_uri(product.get_absolute_url()),
            'product_full_image': product_full_image,
            'product_brand_full_url': product_brand_full_url,
            'likes': regular_likes,
            'partner_likes': partner_likes,
            'referral_sid': referral_sid,
            'alternative': alternative,
            'alternative_url': alternative_url,
            'earning_cut': earning_cut,
            'cost_per_click': cost_per_click,
            'has_share_image': True
        }, context_instance=RequestContext(request),
    )


def product_generate_short_link(request, slug):
    """
    Generate a short product link and return it in a JSON response.
    """
    if not request.user.is_authenticated() or not request.user.is_partner:
        raise Http404

    kwargs = {'published': True}
    product = get_product_from_slug(slug, **kwargs)
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

    return HttpResponsePermanentRedirect(
        reverse('product-redirect', args=(short_product.product_id, 'Ext-Link', short_product.user_id)))


def domain_short_link(request, short_link):
    """
    Takes a short short link and redirect to associated url.
    """
    try:
        url, name, user_id = ShortDomainLink.objects.get_short_domain_for_link(short_link)
    except ShortDomainLink.DoesNotExist:
        raise Http404

    if user_id is None:
        user_id = 0

    return render(request, 'redirect_no_product.html',
                  {'redirect_url': url, 'name': name, 'user_id': user_id, 'page': 'Ext-Link', 'event': 'BuyReferral'})


def product_redirect(request, pk, page='Default', sid=0):
    """
    Display a html redirect page for product pk and page/sid combo.
    """
    product = get_object_or_404(Product, pk=pk, published=True)

    if not page.startswith('Ext'):
        cookie_data = request.get_signed_cookie(REFERRAL_COOKIE_NAME, default=False)
        if cookie_data:
            # Replaces sid and page with data from cookie
            cookie_id, sid, page, _ = cookie_data.split('|')

    store = None
    price = None
    if product.default_vendor:
        store = product.default_vendor.vendor.name
        price = floatformat(product.default_vendor.lowest_price_in_sek, 0)
    else:
        logger.error('Could not find vendor for product id %s' % (pk,))
    url = vendor_buy_url(pk, product.default_vendor, sid, page)
    data = {'id': product.pk,
            'redirect_url': url,
            'store': store,
            'price': price,
            'slug': product.slug,
            'page': page,
            'sid': sid}

    return render(request, 'redirect.html', data)


@require_POST
def product_track(request, pk, page='Default', sid=0):
    """
    Fires a product_buy_click task when called.
    """
    posted_referer = request.POST.get('referer', '')
    client_referer = get_client_referer(request)
    if posted_referer == client_referer and 'redirect' in client_referer:
        return HttpResponse()

    product = None
    try:
        product = get_model('apparel', 'Product').objects.get(pk=pk)
    except get_model('apparel', 'Product').DoesNotExist:
        pass

    response = HttpResponse()
    if product:
        cookie_already_exists = bool(request.COOKIES.get(product.slug, None))
        product_buy_click.delay(pk, '%s\n%s' % (posted_referer, client_referer), get_client_ip(request),
                                get_user_agent(request), sid, page, cookie_already_exists)
        response.set_cookie(product.slug, '1', settings.APPAREL_PRODUCT_MAX_AGE)
    else:
        product_buy_click.delay(pk, '%s\n%s' % (posted_referer, client_referer), get_client_ip(request),
                                get_user_agent(request), sid, page, False)
    return response


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
            product_result['liked'] = ProductLike.objects.filter(product=product, active=True,
                                                                 user=request.user).exists()
            # product_result['likes'] = ProductLike.objects.filter(product=product, active=True).count()

        result.append(product_result)

    return HttpResponse(json.dumps(result), mimetype='application/json')


def look_popup(request):
    look_ids = []
    try:
        look_ids = map(int, request.GET.get('id', '').split(','))
    except ValueError:
        pass

    result = []

    content_type = ContentType.objects.get_for_model(Look)
    for look in look_ids:
        temp_result = {'liked': False}
        if request.user and request.user.is_authenticated():
            temp_result['liked'] = LookLike.objects.filter(look=look, active=True, user=request.user).exists()
            # product_result['likes'] = ProductLike.objects.filter(product=product, active=True).count()

        result.append(temp_result)

    return HttpResponse(json.dumps(result), mimetype='application/json')


@login_required
def product_action(request, pk, action):
    """
    Like or unlike a product through ajax.
    """
    if not request.user or not request.user.is_authenticated():
        return HttpResponse(json.dumps(dict(success=False, error_message='Not authenticated')),
                            mimetype='application/json')
    if request.method == 'GET':
        return HttpResponse(json.dumps(dict(success=False, error_message='Requires POST')), mimetype='application/json')
    if action not in ['like', 'unlike']:
        return HttpResponse(json.dumps(dict(success=False, error_message='Unknown command')),
                            mimetype='application/json')

    try:
        product = Product.objects.get(pk=pk)
    except (Product.MultipleObjectsReturned, Product.DoesNotExist) as e:
        return HttpResponse(json.dumps(dict(success=False, error_message='No product found')),
                            mimetype='application/json')

    return _product_like(request, product, action)


@login_required
def product_like(request, slug, action):
    """
    Like or unlike a product through ajax.
    """
    if not request.user.is_authenticated():
        return HttpResponse(json.dumps(dict(success=False, error_message='Not authenticated')),
                            mimetype='application/json')
    if request.method == 'GET':
        return HttpResponse(json.dumps(dict(success=False, error_message='Requires POST')), mimetype='application/json')
    if action not in ['like', 'unlike']:
        return HttpResponse(json.dumps(dict(success=False, error_message='Unknown command')),
                            mimetype='application/json')

    try:
        product = Product.objects.get(slug=slug)
    except (Product.MultipleObjectsReturned, Product.DoesNotExist) as e:
        return HttpResponse(json.dumps(dict(success=False, error_message='No product found')),
                            mimetype='application/json')

    return _product_like(request, product, action)


def _product_like(request, product, action):
    if action == 'like':
        if request.user.fb_share_like_product:
            facebook_user = get_facebook_user(request)
            if facebook_user:
                facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'like', 'object',
                                          request.build_absolute_uri(product.get_absolute_url()))
    elif action == 'unlike':
        facebook_user = get_facebook_user(request)
        if facebook_user:
            facebook_pull_graph.delay(request.user.pk, facebook_user.access_token, 'like', 'object',
                                      request.build_absolute_uri(product.get_absolute_url()))

    default_active = True if action == 'like' else False
    product_like, created = ProductLike.objects.get_or_create(user=request.user, product=product,
                                                              defaults={'active': default_active})
    if not created:
        product_like.active = default_active
        product_like.save()

    if request.user.owner_network:
        owner_user = request.user.owner_network
        if owner_user.is_subscriber:
            product_like, created = ProductLike.objects.get_or_create(user=owner_user, product=product,
                                                                      defaults={'active': default_active})
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
        return HttpResponse(json.dumps(dict(success=False, error_message='Not authenticated')),
                            mimetype='application/json')
    if action not in ['like', 'unlike']:
        return HttpResponse(json.dumps(dict(success=False, error_message='Unknown command')),
                            mimetype='application/json')

    try:
        look = Look.objects.get(slug=slug)
    except (Look.MultipleObjectsReturned, Look.DoesNotExist) as e:
        return HttpResponse(json.dumps(dict(success=False, error_message='No look found')), mimetype='application/json')

    if action == 'like':
        if request.user.fb_share_like_look:
            facebook_user = get_facebook_user(request)
            if facebook_user:
                facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'like', 'object',
                                          request.build_absolute_uri(look.get_absolute_url()))
    elif action == 'unlike':
        facebook_user = get_facebook_user(request)
        if facebook_user:
            facebook_pull_graph.delay(request.user.pk, facebook_user.access_token, 'like', 'object',
                                      request.build_absolute_uri(look.get_absolute_url()))

    default_active = True if action == 'like' else False
    look_like, created = LookLike.objects.get_or_create(user=request.user, look=look,
                                                        defaults={'active': default_active})
    if not created:
        look_like.active = default_active
        look_like.save()

    if not (look.user == request.user):
        NotificationEvent.objects.push_notification(look.user, "LIKELOOK", request.user, look=look)

    if action == 'like':
        process_like_look_created.delay(look.user, request.user, look_like)

    look_popularity.delay(look)

    return HttpResponse(json.dumps(dict(success=True, error_message=None)), mimetype='application/json')


def look_list(request, search=None, contains=None, gender=None):
    """
    This view can list looks in four ways:

        1) If no argument is used a list of all looks is displayed.
        2) If popular-argument is set displays a list of all popular looks in your network.
        3) If search-argument is set displays a list of all matching looks to param 'q'.
        4) If contains-argument is set displays all looks that contains the product.

    """
    gender = select_from_multi_gender(request, 'look', gender)
    gender_list = {'A': ['W', 'M', 'U'],
                   'M': ['M', 'U'],
                   'W': ['W', 'U']}

    queryset = Look.published_objects.filter(user__is_hidden=False)

    # add different tabs views
    view = request.GET.get('view', 'all')
    profile = request.user
    is_authenticated = request.user.is_authenticated()

    if search:
        if not gender or gender == 'A':
            gender_field = 'gender:(U OR M OR W)'
        else:
            gender_field = 'gender:(U OR %s)' % (gender,)
        query_arguments = {'qf': 'text',
                           'defType': 'edismax',
                           'fq': ['django_ct:apparel.look', gender_field],
                           'start': 0,
                           'rows': 500}  # XXX: maximum search results, sync this with the count that is displayed in the search result box
        results = ApparelSearch(request.GET.get('q'), **query_arguments)
        queryset = queryset.filter(id__in=[doc.django_id for doc in results.get_docs()])
    elif view and view != 'all':
        if view == 'latest' or 'f' in request.GET:
            queryset = queryset.filter(published=True).filter(gender__in=gender_list.get(gender)).order_by('-created')
        elif view == 'friends':
            user_ids = []
            if is_authenticated:
                user_ids = get_model('profile', 'Follow').objects.filter(user=request.user, active=True).values_list(
                    'user_follow_id', flat=True)
                queryset = queryset.filter(gender__in=gender_list.get(gender)).filter(user__in=user_ids).order_by(
                    '-created')
    elif contains:
        queryset = queryset.filter(components__product__slug=contains).distinct()
    else:
        queryset = queryset.filter(gender__in=gender_list.get(gender)).order_by('-popularity', 'created')

    paged_result = get_paged_result(queryset, LOOK_PAGE_SIZE, request.GET.get('page', 1))

    if request.is_ajax():
        return render(request, 'apparel/fragments/look_list.html', {
            'current_page': paged_result,
            'objects_list': paged_result,
        })

    #return HttpResponseRedirect()
    return render(request, 'apparel/look_list.html', {
        'query': request.GET.get('q'),
        'paginator': paged_result.paginator,
        'current_page': paged_result,
        'next': request.get_full_path(),
        'gender': gender,
    })


def look_detail(request, slug):
    look = get_object_or_404(get_model('apparel', 'Look'), slug=slug)
    # Only show unpublished looks to creator
    if not look.published and look.user != request.user:
        raise Http404()

    is_liked = False
    if request.user.is_authenticated():
        is_liked = LookLike.objects.filter(user=request.user, look=look, active=True).exists()

    looks_by_user = Look.published_objects.filter(user=look.user).exclude(pk=look.id).order_by('-modified')[:4]

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
                    facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'create', 'look',
                                              request.build_absolute_uri(look.get_absolute_url()))
        else:
            look_saved = request.session['look_saved']

        del request.session['look_saved']

    # Likes
    likes = look.likes.filter(active=True, user__is_hidden=False).order_by('-modified').select_related('user')

    # Base url
    base_url = request.build_absolute_uri('/')[:-1]

    wrapper_element = {'width': '100', 'height': '100'}

    # Components
    if look.display_with_component == 'C':
        components = look.collage_components.select_related('product')
        # look image is responsible for scaling the look view. Since the look width and height might not be different we need to rescale
        wrapper_element = {'width': '96', 'height': '96'}
    elif look.display_with_component == 'P':
        components = look.photo_components.select_related('product')

    for component in components:
        component.style_embed = component._style(min(694, look.image_width) / float(look.width))
    # Build static image if it is missing
    if not look.static_image:
        build_static_look_image(look.pk)
        look = get_model('apparel', 'Look').objects.get(pk=look.pk)

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
            'base_url': base_url,
            'is_liked': is_liked,
            'wrapper_element': wrapper_element,
            'resolution': '%sx%s' % (look.width, look.height,),
            'has_share_image': True
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
            facebook_pull_graph.delay(request.user.pk, facebook_user.access_token, 'create', 'look',
                                      request.build_absolute_uri(look.get_absolute_url()))

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
    return render_to_response('403.html', {'is_csrf': True, 'debug': settings.DEBUG, 'reason': reason},
                              context_instance=RequestContext(request))


def list_colors(request):
    color_data = get_model('apparel', 'Option').objects.filter(option_type__name__in=['color', 'pattern']).exclude(
        value__exact='').values_list('value', flat=True)

    callback = request.GET.get('callback')
    if callback:
        return JSONPResponse(list(color_data), callback=callback)

    return JSONResponse(list(color_data))


def list_categories(request):
    categories = {}
    return_categories = []

    last_level = 0
    category_query = get_model('apparel', 'Category').objects.values('name_en', 'name_sv', 'pk', 'parent_id', 'level')
    for category in category_query:
        category_tuple = (category.get('name_en'), category.get('name_sv'), [])

        categories[category.get('pk')] = category_tuple

        if category.get('level') > last_level:
            categories[category.get('parent_id')][2].append(category_tuple)
        else:
            return_categories.append(category_tuple)

    callback = request.GET.get('callback')
    if callback:
        return JSONPResponse(return_categories, callback=callback)

    return JSONResponse(return_categories)


@ensure_csrf_cookie
def authenticated_backend(request):
    profile = None
    if request.user and request.user.is_authenticated():
        profile = request.build_absolute_uri(request.user.get_absolute_url())
    return JSONResponse({'authenticated': request.user and request.user.is_authenticated(), 'profile': profile})


def product_lookup_by_domain(request, domain, key):
    model = get_model('apparel', 'DomainDeepLinking')
    domain = extract_domain_with_suffix(domain)
    logger.info("Lookup by domain, will try and find a match for domain [%s]" % domain)
    # domain:          example.com
    # Deeplink.domain: example.com/se
    results = model.objects.filter(domain__icontains=domain)
    instance = None
    if not results:
        logger.info("No domain found for %s, returning 404" % domain)
        raise Http404

    if len(results) > 1:
        for item in results:
            if item.domain in key:
                instance = item
    else:
        instance = results[0]

    if instance and instance.template:
        logger.info("Domain [%s / %s] was a match for %s." % (instance.domain, instance.vendor, domain))
        user_id = request.user.pk
        key_split = urlparse.urlsplit(key)
        ulp = urlparse.urlunsplit(('', '', key_split.path, key_split.query, key_split.fragment))
        url = key
        return instance.template.format(sid='{}-0-Ext-Link'.format(user_id), url=url, ulp=ulp), instance.vendor
    return None, None


def product_lookup_by_solr(request, key):
    logger.info("Trying to lookup %s from SOLR." % key)
    kwargs = {'fq': ['product_key:\"%s\"' % (key,)], 'rows': 1, 'django_ct': "apparel.product"}
    connection = Solr(settings.SOLR_URL)
    result = connection.search("*", **kwargs)

    dict = result.__dict__
    logger.info("Query executed in %s milliseconds" % dict['qtime'])

    if dict['hits'] < 1:
        logger.info("No results found for key %s." % key)
        return None
    logger.info("%s results found" % dict['hits'])
    product_id = dict['docs'][0]['django_id']

    return int(product_id)


# TODO: Offending the DRY principle
def product_lookup_solr_fragment(key, vendor_id=None):
    logger.info("Trying to lookup %s from SOLR." % key)
    #qs_string = "%s" %
    try:
        key = str(SQ(product_key=key))
    except:
        key = str(SQ(product_key=key.encode('utf-8')))
    qs = embed_wildcard_solr_query( key )
    kwargs = {'fq': [qs], 'rows': 1, 'django_ct': "apparel.product"}
    if vendor_id:
        kwargs['fq'].append('store_id:\"%s\"' % (vendor_id,))
    connection = Solr(settings.SOLR_URL)
    result = connection.search("*", **kwargs)

    dict = result.__dict__
    logger.info("Query executed in %s milliseconds" % dict['qtime'])

    if dict['hits'] < 1:
        logger.info("No results found for key %s." % key)
        return None
    logger.info("%s results found" % dict['hits'])
    product_id = dict['docs'][0]['django_id']

    return int(product_id)


def parse_luisaviaroma_fragment(fragment):
    try:
        seasonId = re.search(r'SeasonId=(\w+)?', fragment).group(1)
        collectionId = re.search(r'CollectionId=(\w+)?', fragment).group(1)
        itemId = re.search(r'ItemId=(\w+)?', fragment).group(1).zfill(3)
        return "%s-%s%s" % (seasonId, collectionId, itemId)
    except AttributeError:
        return None


def extract_asos_nelly_product_url(url, is_nelly_product=False):
    parsedurl = urlparse.urlsplit(url)
    path = parsedurl.path
    key = None
    vendor_id = None
    if ("nelly" in parsedurl.netloc):
        if is_nelly_product:
            # get rid of categories for nelly links, only keep product name (last two "/"")
            temp_path = path.rstrip('/')  # remove last slash if it exists
            key = temp_path.split('/')[-1]  # get the "righest" element after a slash
            key = "/%s/" % key
            try:
                vendor_id = get_model('apparel', 'Vendor').objects.get(name="Nelly").id
            except get_model('apparel', 'Vendor').DoesNotExist:
                logger.warning("Vendor Nelly does not exist")
    elif ("asos" in parsedurl.netloc):
        search_result = re.search(r'iid=(\w+)?', parsedurl.query)
        if search_result:
            prodId = search_result.group(1)
            key = "%s?iid=%s" % (path, prodId)

    elif ("luisaviaroma" in parsedurl.netloc):
        if parsedurl.fragment:  # the "original" links don't have this, they should never land here though
            key = parse_luisaviaroma_fragment(parsedurl.fragment)
        else:
            key = url
    return (key, vendor_id)


def product_lookup_asos_nelly(url, is_nelly_product=False):
    key, vendor_id = extract_asos_nelly_product_url(url, is_nelly_product)
    # key = urllib.quote_plus(key)
    if key:
        product_pk = product_lookup_solr_fragment(key, vendor_id)
        if product_pk:
            return product_pk

    return None
    #json_data = json.loads(products[0].json)
    #return json_data.get('site_product', None)


def product_lookup(request):
    if not request.user.is_authenticated():
        raise Http404
    key = smart_unicode(urllib.unquote(smart_str(request.GET.get('key', ''))))
    logger.info("Request to lookup product for %s sent, trying to extract PK from request." % key)
    try:
        product_pk = long(smart_unicode(urllib.unquote(smart_str(request.GET.get('pk', '')))))
    except ValueError:
        product_pk = None
        logger.info("No clean Product pk extracted.")

    is_nelly_product = request.GET.get('is_product', False)

    original_key = key
    if key and not product_pk:
        product_pk = product_lookup_by_solr(request, key)
        if not product_pk:
            logger.info("Failed to extract product from solr, will change the protocol and try again.")
            if key.startswith('https'):
                key = key.replace('https', 'http')
            elif key.startswith('http'):
                temp = list(key)
                temp.insert(4, 's')
                key = ''.join(temp)
            product_pk = product_lookup_by_solr(request, key)
            if not product_pk:
                logger.info("Failed to extract product from solr for %s" % key)
                product_pk = product_lookup_asos_nelly(original_key, is_nelly_product)
            else:
                logger.info("Successfully found product in SOLR for key %s" % key)
        else:
            logger.info("Successfully found product in SOLR for key %s" % key)
    # TODO: must go through theimp database right now to fetch site product by real url
    # key = smart_unicode(urllib.unquote(smart_str(request.GET.get('key', ''))))
    #imported_product = get_object_or_404(get_model('theimp', 'Product'), key__startswith=key)


    #json_data = json.loads(imported_product.json)
    #product_pk = json_data.get('site_product', None)
    product_short_link = None
    product_link = None
    product_liked = False
    if product_pk:
        product = get_object_or_404(Product, pk=product_pk, published=True)
        product_link = request.build_absolute_uri(product.get_absolute_url())
        product_short_link, created = ShortProductLink.objects.get_or_create(product=product, user=request.user)
        product_short_link_str = reverse('product-short-link', args=[product_short_link.link()])
        product_short_link_str = request.build_absolute_uri(product_short_link_str)
        logger.info("Product match found for key, creating short product link [%s]." % product_short_link_str)
        product_liked = get_model('apparel', 'ProductLike').objects.filter(user=request.user, product=product,
                                                                           active=True).exists()
    else:
        domain = smart_unicode(urllib.unquote(smart_str(request.GET.get('domain', ''))))
        logger.info("No product found for key, falling back to domain deep linking.")
        product_short_link_str, vendor = product_lookup_by_domain(request, domain, original_key)
        logger.info("No product found for key, falling back to domain deep linking.")
        if product_short_link_str is not None:
            product_short_link, created = ShortDomainLink.objects.get_or_create(url=product_short_link_str,
                                                                                user=request.user, vendor=vendor)
            product_short_link_str = reverse('domain-short-link', args=[product_short_link.link()])
            product_short_link_str = request.build_absolute_uri(product_short_link_str)

    return JSONResponse({
        'product_pk': product_pk,
        'product_link': product_link,
        'product_short_link': product_short_link_str,
        'product_liked': product_liked
    })


@login_required
@require_POST
def follow_backend(request):
    follows = []
    uids = request.POST.get('uids')
    if uids:
        uids = uids.split(',')
        for profile in get_user_model().objects.filter(id__in=uids):
            follow_html = render_to_string('apparel/fragments/follow.html', {'profile': profile},
                                           context_instance=RequestContext(request))
            follows.append({'id': profile.pk, 'html': follow_html})

    return HttpResponse(json.dumps(follows), mimetype='application/json')


def user_list(request, gender=None, brand=False):
    """
    Displays a list of profiles
    """
    gender = select_from_multi_gender(request, 'user', gender)
    gender_list = {'A': ['W', 'M', 'U'],
                   'M': ['M', 'U'],
                   'W': ['W', 'U']}

    queryset = get_user_model().objects.filter(is_active=True,
                                               is_brand=brand,
                                               is_hidden=False,
                                               advertiser_store__isnull=True)

    if not brand:
        queryset = queryset.filter(Q(gender__in=gender_list.get(gender)) | Q(gender__isnull=True))
    else:
        # XXX: is this solution good enough?
        # XXX: nope, too slow
        # queryset = queryset.filter(brand__products__availability=True, brand__products__published=True, brand__products__gender__in=gender_list.get(gender)).distinct()
        queryset = queryset.filter(Q(gender__in=gender_list.get(gender)) | Q(gender__isnull=True))

    extra_parameter = None

    alphabet = request.GET.get('alphabet')
    if alphabet:
        if alphabet == '0-9':
            queryset = queryset.filter(name__regex=r'^\d.+')
        elif alphabet in string.lowercase:
            queryset = queryset.filter(name__istartswith=alphabet)

        extra_parameter = 'alphabet=%s' % (alphabet,)

    queryset = queryset.order_by('-popularity', '-followers_count', 'first_name', 'last_name', 'username')

    paged_result = get_paged_result(queryset, 12, request.GET.get('page', '1'))

    if request.is_ajax():
        return render(request, 'apparel/fragments/user_list.html', {
            'current_page': paged_result,
            'extra_parameter': extra_parameter,
        })

    return render(request, 'apparel/user_list.html', {
        'current_page': paged_result,
        'next': request.get_full_path(),
        'alphabet': string.lowercase,
        'selected_alphabet': alphabet,
        'is_brand': brand,
        'extra_parameter': extra_parameter,
        'gender': gender
    })


#
# Index page for unauthenticated users
#

def index(request, gender=None):
    if request.user.is_authenticated():
        # dirty fix: when you are logged in and don't specifiy a gender via url, you should get the gender of your account
        if gender == 'none':
            gender = None
        return user_feed(request, gender=gender)

    return render(request, 'apparel/home.html', {'featured': get_featured_activity_today()})


def about(request):
    return render(request, 'apparel/about.html')

def contact(request):
    return render(request, 'apparel/contact.html')


def jobs(request):
    return render(request, 'apparel/jobs.html')


def founders(request):
    return render(request, 'apparel/founders.html')

def community(request):
    return render(request, 'apparel/index.html')

# Temporary url for onboarding page (work in progress)
def onboarding(request):
    return render(request, 'apparel/onboarding.html')


#
# Contest Stylesearch
#

def contest_stylesearch(request):
    image = 'images/stylesearch.png'
    if request.LANGUAGE_CODE == 'sv':
        image = 'images/stylesearch_sv.png'

    return render(request, 'apparel/contest_stylesearch.html', {'image': image})


def contest_stylesearch_charts(request):
    start_date = datetime.datetime(2013, 8, 26, 0, 0, 0)
    end_date = datetime.datetime(2013, 9, 1, 23, 59, 59)

    looks = get_model('apparel', 'Look').published_objects.filter(created__range=(start_date, end_date),
                                                                  published=True) \
                .filter(likes__created__lte=end_date, likes__active=True) \
                .annotate(num_likes=Count('likes')) \
                .select_related('user') \
                .order_by('-num_likes', 'created')[:10]

    return render(request, 'apparel/contest_stylesearch_charts.html', {'looks': looks})


#
# Contest XMAS
#

def contest_xmas_menlook(request):
    user_slug = 'menlook'
    if settings.DEBUG:
        user_slug = 'adminuser'

    profile = get_user_model().objects.get(slug=user_slug)

    is_closed = False
    end_date = datetime.datetime(2013, 12, 8, 23, 59, 59)
    if settings.DEBUG:
        end_date = datetime.datetime(2013, 12, 8, 21, 59, 59)
    if timezone.now() > end_date:
        is_closed = True

    return render(request, 'apparel/contest_xmas_menlook.html', {'profile': profile, 'is_closed': is_closed})


def contest_xmas_menlook_charts(request):
    start_date = datetime.datetime(2013, 11, 20, 0, 0, 0)
    end_date = datetime.datetime(2013, 12, 8, 23, 59, 59)

    vendor_id = 71
    if settings.DEBUG:
        vendor_id = 59
        end_date = datetime.datetime(2013, 12, 8, 21, 59, 59)
        start_date = datetime.datetime(2013, 11, 19, 0, 0, 0)

    is_closed = False
    if timezone.now() > end_date:
        is_closed = True

    valid_looks = get_model('apparel', 'Look').published_objects.filter(components__product__vendors=vendor_id) \
        .annotate(num_products=Count('components__product')) \
        .filter(num_products__gte=5, published=True)

    looks = get_model('apparel', 'Look').published_objects.filter(created__range=(start_date, end_date),
                                                                  published=True,
                                                                  likes__created__lte=end_date,
                                                                  likes__active=True,
                                                                  pk__in=valid_looks) \
                .exclude(pk__in=[1497]) \
                .annotate(num_likes=Count('likes')) \
                .select_related('user') \
                .order_by('-num_likes', 'created')[:10]

    return render(request, 'apparel/contest_xmas_menlook_charts.html', {'looks': looks, 'is_closed': is_closed})


#
# Contest TOPMODEL
#


def topmodel_user_list(request):
    """
    Displays a list of profiles
    """
    queryset = None

    if settings.DEBUG:
        queryset = get_user_model().objects.filter(id__in=[1, 2, 3, 4, 5])
    else:
        queryset = get_user_model().objects.filter(last_name='- Top Model')

    extra_parameter = None
    queryset = queryset.order_by('-followers_count', 'first_name', 'last_name')
    paged_result = get_paged_result(queryset, 20, request.GET.get('page', '1'))

    if request.is_ajax():
        return render(request, 'apparel/fragments/user_list.html', {
            'current_page': paged_result,
            'extra_parameter': extra_parameter,
        })

    return render(request, 'apparel/topmodel_list.html', {
        'current_page': paged_result,
        'next': request.get_full_path(),
        'extra_parameter': extra_parameter,
    })


def contest_topmodel(request):
    image = 'images/topmodel.png'
    if request.LANGUAGE_CODE == 'sv':
        image = 'images/topmodel_sv.png'

    return render(request, 'apparel/contest_topmodel.html', {'image': image})


#
# Contest JC
#

def contest_jc(request):
    return render(request, 'apparel/contest_jc.html', {})


def contest_jc_charts(request):
    start_date = datetime.datetime(2014, 6, 6, 0, 0, 0)
    end_date = datetime.datetime(2014, 8, 30, 23, 59, 59)

    category_id = 288
    if settings.DEBUG:
        category_id = 6
        start_date = datetime.datetime(2014, 1, 1, 0, 0, 0)
        end_date = datetime.datetime(2014, 8, 30, 23, 59, 59)
    is_closed = False
    if timezone.now() > end_date:
        is_closed = True

    valid_looks = get_model('apparel', 'Look').published_objects.filter(components__product__category=category_id,
                                                                        published=True)

    looks = get_model('apparel', 'Look').published_objects.filter(created__range=(start_date, end_date), published=True,
                                                                  likes__created__lte=end_date,
                                                                  likes__active=True,
                                                                  pk__in=valid_looks) \
                .annotate(num_likes=Count('likes')) \
                .select_related('user') \
                .order_by('-num_likes', 'created')[:10]

    return render(request, 'apparel/contest_jc_charts.html', {'looks': looks, 'is_closed': is_closed})


def apparel_set_language(request):
    language = request.POST.get('locale', translation.get_language())
    if request.user.is_authenticated() and request.user.language != language:
        request.user.language = language
        request.user.save()

    return change_locale(request)


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


def extract_domain_with_suffix(domain):
    try:
        tld_ext = tldextract.TLDExtract(cache_file=False)
        extracted = tld_ext(domain)
        return "%s.%s" % (extracted.domain, extracted.suffix)
    except Exception, msg:
        logger.info("Domain supplied could not be extracted: %s [%s]" % (domain, msg))
        return None


# Todo: move this to product manager (also deprecated now since 20151020)
def extract_apparel_product_with_url(key):
    return get_model('apparel', 'Product').objects.filter(published=True, product_key__icontains=key)

def embed_wildcard_solr_query(qs_string):
    return "%s*%s*" % (qs_string[:qs_string.index(':')+1],qs_string[qs_string.index(':')+1:])

