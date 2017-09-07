# -*- coding: utf-8 -*-
import decimal
import logging
import re
import urllib
import urlparse

import simplejson
import tldextract
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import get_model
from django.http import Http404
from django.http.response import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.utils.encoding import smart_unicode, smart_str, DjangoUnicodeDecodeError
from django.views.decorators.csrf import csrf_exempt
from pysolr import Solr
from simplejson import JSONDecodeError
from solrq import Q as SQ

from apparelrow.apparel.models import Product
from apparelrow.apparel.models import ShortProductLink, ShortDomainLink
from apparelrow.apparel.models import get_cuts_for_user_and_vendor
from apparelrow.apparel.utils import JSONResponse, get_location_warning_text, generate_sid, get_vendor_cost_per_click
from apparelrow.dashboard.utils import parse_rules_exception
from apparelrow.profile.models import User
from product_match.models import UrlDetail

logger = logging.getLogger("apparelrow")


# Create your views here.

def match_product(product_id, computed_url):
    # This method will try to primarily to match urls got by chrome or safari extension
    pass


def switch_url_candidate(key):
    if key is None:
        logger.error("Cannot switch Key if None is the keys value")
        raise TypeError

    if key and key.startswith('https://') and not key.endswith('/'):
        key = key + '/'
    elif key and key.startswith('https://') and key.endswith('/'):
        key = key.replace('https', 'http', 1)
        key = key.rstrip('/')
    elif key and key.startswith('http://') and not key.endswith('/'):
        key = key + '/'
    elif key and key.startswith('http://') and key.endswith('/'):
        key = key.replace("http", "https", 1)
        key = key.rstrip('/')
    else:
        # This should never happen
        logger.error("Key did not match any of the switch url candidate cases")
        raise ValueError

    return key


def try_extract_product_pk(url_candidate):
    product_pk = None
    url_combination_tries_left = 4
    original_key = url_candidate

    while url_candidate and not product_pk and url_combination_tries_left > 0:
        product_pk = UrlDetail.objects.filter(url=url_candidate).values_list('product_id', flat=True)
        #product_pk.get().product_id
        if not product_pk:
            url_candidate = switch_url_candidate(url_candidate)
            url_combination_tries_left -= 1
        if product_pk:
            url_combination_tries_left = 0

    if not product_pk:
        #parsed_url = urlparse.urlsplit(original_key)
        product_pk = find_url(original_key)
        # modified_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

    return product_pk


def extract_product_lookup_domain(GET, POST, key):
    sent_domain = GET.get('domain', '') or POST.get('domain', '')
    domain = smart_unicode(urllib.unquote(smart_str(sent_domain))) or key
    return domain


def extract_encoded_url_string(url):
    try:
        key = smart_unicode(smart_str(url))
    except DjangoUnicodeDecodeError:
        key_string = url.decode("iso-8859-1")
        key = smart_unicode(smart_str(key_string))
    return key


def extract_product_lookup_key(GET, POST):
    sent_key = GET.get('key', '') or POST.get('key', '')
    url = extract_encoded_url_string(sent_key)
    key = extract_encoded_url_string(urllib.unquote(url.encode('utf-8')))
    return key


def remove_query_parameters_from_url(key):
    if key is None:
        logger.error("Cannot remove query parameters from a None Key")
        raise TypeError
    else:
        parsed_url = urlparse.urlsplit(key)
        modified_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

    return modified_url


def build_link(request, url):
    link = request.build_absolute_uri(url)
    return link


def get_product_short_link_for_found_product_pk(product, request):
    product_short_link, _ = ShortProductLink.objects.get_or_create(product=product, user=request.user)
    product_short_link_str = reverse('product-short-link', args=[product_short_link.link()])
    product_short_link_str = build_link(request, product_short_link_str)
    logger.info(u"Product match found for key, creating short product link [%s]." % product_short_link_str)
    return product_short_link_str


def get_product_earning_for_found_product_pk(product, request, vendor):
    # Only adds approx to earning text when user does not earn CPC for all stores

    approx_text = "approx. "
    if request.user and request.user.partner_group and request.user.partner_group.has_cpc_all_stores:
        approx_text = ""
    product_earning = None
    earning, currency = product.default_vendor.get_product_earning(request.user)
    if earning and currency:
        help_text = "sale" if vendor.is_cpo else "click"
        product_earning = "You will earn %s%s %s per generated %s of this item." % (
            approx_text, currency, earning, help_text)
    return product_earning


def parse_found_product_pk(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk, published=True)
    product_link = build_link(request, product.get_absolute_url())
    product_short_link_str = get_product_short_link_for_found_product_pk(product, request)
    product_liked = get_model('apparel', 'ProductLike').objects.filter(user=request.user, product=product,
                                                                       active=True).exists()
    product_name = product.get_product_name_to_display

    vendor = product.default_vendor.vendor
    product_earning = get_product_earning_for_found_product_pk(product, request, vendor)
    return product_link, product_short_link_str, product_liked, product_name, vendor, product_earning


def parse_not_found_product_pk(domain, original_key, request):
    logger.info(u"No product found for key, falling back to domain deep linking.")

    approx_text = "approx. "
    if request.user and request.user.partner_group and request.user.partner_group.has_cpc_all_stores:
        approx_text = ""

    product_short_link_str, vendor = get_short_domain_deeplink(domain, original_key, request.user.id)

    if product_short_link_str is not None:
        product_short_link_str = build_link(request, product_short_link_str)
        _, cut, _, publisher_cut = get_cuts_for_user_and_vendor(request.user.id, vendor)

        if request.user.partner_group and request.user.partner_group.has_cpc_all_stores:
            product_earning = get_product_earning_group(vendor, request.user, publisher_cut, approx_text)
        else:
            product_earning = get_product_earning_standalone(vendor, cut, publisher_cut, approx_text)
    else:
        logger.error("The requested page cannot be found")
        raise Http404
    return product_earning, product_short_link_str, vendor


def extract_url_and_domain(request):
    get_request = request.GET.copy()
    post_request = request.POST.copy()

    url = extract_product_lookup_key(get_request, post_request)
    domain = extract_product_lookup_domain(get_request, post_request, url)
    return url, domain


def get_warning_text(vendor, request):
    if vendor:
        vendor_markets = vendor.location_codes_list()
    warning_text = get_location_warning_text(vendor_markets, request.user, "chrome-ext")
    decoded_warning_text = warning_text.decode()
    return decoded_warning_text


@csrf_exempt
def lookup_products(request):
    #    if not request.user.is_authenticated():
    #        raise Http404
    request.user = User.objects.all().latest("date_joined")
    product_link = None
    product_liked = False
    product_name = None

    original_key, domain = extract_url_and_domain(request)
    # url_candidate = remove_query_parameters_from_url(original_key)

    product_pk = try_extract_product_pk(original_key)

    if product_pk:
        product_link, product_short_link_str, product_liked, product_name, vendor, product_earning = \
            parse_found_product_pk(request, product_pk)

    else:

        product_earning, product_short_link_str, vendor = parse_not_found_product_pk(domain, original_key, request)

    decoded_warning_text = get_warning_text(vendor, request)

    return JSONResponse({
        'product_pk': product_pk,
        'product_link': product_link,
        'product_short_link': product_short_link_str,
        'product_liked': product_liked,
        'product_name': product_name,
        'product_earning': product_earning,
        'warning_text': decoded_warning_text
    })


def find_url(original_key):
    parsed_url = urlparse.urlsplit(original_key)
    domain = parsed_url.netloc
    path = parsed_url.path
    query = parsed_url.query
    fragment = parsed_url.fragment

    query = query.lower()

    if 'id' in query:

        # 'https://www.mq.se/article/alexia_trousers?attr1_id=1347'
        vendor_pid = re.search(r'id=(\w+)?', query).group(1)
        product_id = UrlDetail.objects.get(domain=domain, path=path, parameters__contains=vendor_pid).product_id

    else:
        UrlDetail.objects.get(domain=domain, path=path).product_id

    return product_id
