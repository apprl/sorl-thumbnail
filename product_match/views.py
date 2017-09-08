# -*- coding: utf-8 -*-
import decimal
import logging
import urllib
import urlparse

import tldextract
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import get_model
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.encoding import smart_unicode, smart_str, DjangoUnicodeDecodeError
from django.views.decorators.csrf import csrf_exempt

from apparelrow.apparel.models import Product
from apparelrow.apparel.models import ShortProductLink, ShortDomainLink
from apparelrow.apparel.models import get_cuts_for_user_and_vendor
from apparelrow.apparel.utils import JSONResponse, get_location_warning_text, get_vendor_cost_per_click, \
    get_external_store_commission, generate_sid
from apparelrow.dashboard.utils import parse_rules_exception
from apparelrow.profile.models import User
from product_match.models import UrlDetail
from product_match.utils import get_domain, get_vendor_params, match_urls

logger = logging.getLogger("apparelrow")


# Create your views here.

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
        # product_pk.get().product_id
        if not product_pk:
            url_candidate = switch_url_candidate(url_candidate)
            url_combination_tries_left -= 1
        if product_pk:
            url_combination_tries_left = 0

    if not product_pk:
        parsed_url = urlparse.urlsplit(original_key)
    # product_pk = find_url(original_key)
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


def get_product_earning_standalone(vendor, cut, publisher_cut, approx_text):
    earning_cut = cut * publisher_cut
    product_earning = None
    if vendor and earning_cut:
        if vendor.is_cpo:
            store_commission = get_vendor_commission(vendor)
            if store_commission:
                earning_cut = earning_cut * store_commission
                product_earning = u"You will earn %s%.2f %% of the total sale value from this store." % \
                                  (approx_text, earning_cut * 100)
        elif vendor.is_cpc:
            cost_per_click = get_vendor_cost_per_click(vendor)
            if cost_per_click:
                product_earning = u"You will earn %s%s %.2f per generated click when linking to " \
                                  "this retailer" % \
                                  (approx_text, cost_per_click.currency, (earning_cut * cost_per_click.amount))
    return product_earning


def get_vendor_commission(vendor):
    """
    Get commission for Vendor either if it is an AAN Store or any other affiliate network
    """
    if get_model('advertiser', 'Store').objects.filter(vendor=vendor).exists():
        store = get_model('advertiser', 'Store').objects.filter(vendor=vendor)[0]
        return store.commission_percentage
    elif get_model('dashboard', 'StoreCommission').objects.filter(vendor=vendor).exists():
        store_commission = get_model('dashboard', 'StoreCommission').objects.filter(vendor=vendor)
        return get_external_store_commission(store_commission)
    return None


def get_product_earning_group(vendor, user, publisher_cut, approx_text):
    """

    """
    product_earning = ""
    try:
        cut_obj = get_model('dashboard', 'Cut').objects.get(group=user.partner_group, vendor=vendor)
        # For Publishers who earns CPC for all stores, cut is 100% unless exceptions are defined
        normal_cut = 1
        earning_amount = cut_obj.locale_cpc_amount
        # Get exceptions and if they are defined, replace current cuts
        if cut_obj.rules_exceptions:
            cut_exception, publisher_cut_exception, click_cost = parse_rules_exception(cut_obj.rules_exceptions,
                                                                                       user.id)
            if cut_exception:
                normal_cut = cut_exception
            if publisher_cut_exception is not None and user.owner_network:
                publisher_cut = publisher_cut_exception
        publisher_earning = decimal.Decimal(earning_amount * (normal_cut * publisher_cut))
        product_earning = u"You will earn %s%s %.2f per generated click when linking to " \
                          "this retailer" % \
                          (approx_text, cut_obj.locale_cpc_currency, publisher_earning)
    except get_model('dashboard', 'Cut').DoesNotExist:
        logger.warning("Cut for commission group %s and vendor %s does not exist." %
                       (user.partner_group, vendor.name))
    except get_model('dashboard', 'Cut').MultipleObjectsReturned:
        logger.warning("Multiple cuts for commission group %s and vendor %s exist. Please make sure there "
                       "is only one instance of this Cut." % (user.partner_group, vendor.name))

    return product_earning


def extract_domain_with_suffix(domain):
    try:
        tld_ext = tldextract.TLDExtract(cache_file=settings.TLDEXTRACT_CACHE)
        extracted = tld_ext(domain)
        return "%s.%s" % (extracted.domain, extracted.suffix)
    except Exception, msg:
        logger.info("Domain supplied could not be extracted: %s [%s]" % (domain, msg))
        return None


def product_lookup_by_domain(domain, key, user_id):
    model = get_model('apparel', 'DomainDeepLinking')
    domain = extract_domain_with_suffix(domain)
    logger.info(u"Lookup by domain, will try and find a match for domain [%s]" % domain)
    # domain:          example.com
    # Deeplink.domain: example.com/se
    results = model.objects.filter(domain__icontains=domain)
    instance = None
    if not results:
        logger.info("No domain found for %s" % domain)
        return None, None

    if len(results) > 1:
        for item in results:
            if item.domain in key:
                instance = item
    else:
        instance = results[0]

    if instance and instance.template:
        logger.info(u"Domain [%s / %s] was a match for %s." % (instance.domain, instance.vendor, domain))
        key_split = urlparse.urlsplit(key)
        ulp = urlparse.urlunsplit(('', '', key_split.path, key_split.query, key_split.fragment))
        url = key
        sid = generate_sid(0, user_id, 'Ext-Link', url)
        if instance.quote_url:
            url = urllib.quote(url.encode('utf-8'), safe='')
        if instance.quote_sid:
            sid = urllib.quote(sid.encode('utf-8'), safe='')
        if instance.quote_ulp:
            ulp = urllib.quote(ulp.encode('utf-8'), safe='')
        return instance.template.format(sid=sid, url=url, ulp=ulp), instance.vendor
    else:
        return None, None


def get_short_domain_deeplink(domain, original_key, user_id):
    """
    :param domain:
    :param original_key:
    :param user_id:
    :return:
    """
    product_short_link_str, vendor = product_lookup_by_domain(domain, original_key, user_id)
    if product_short_link_str is not None:
        product_short_link, _ = ShortDomainLink.objects.get_or_create(url=product_short_link_str,
                                                                      user_id=user_id, vendor=vendor)
        logger.info(u"Short link: %s" % product_short_link)
        product_short_link_str = reverse('domain-short-link', args=[product_short_link.link()])
    return product_short_link_str, vendor


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
def create_short_links_and_lookup_product(request):
    #    if not request.user.is_authenticated():
    #        raise Http404
    request.user = User.objects.all().latest("date_joined")
    product_link = None
    product_liked = False
    product_name = None

    original_key, domain = extract_url_and_domain(request)
    # product_pk = try_extract_product_pk(original_key)
    domain = get_domain(original_key)
    param = get_vendor_params(domain)
    product_id = match_urls(original_key, param)


    if product_id:
        product_link, product_short_link_str, product_liked, product_name, vendor, product_earning = \
            parse_found_product_pk(request, product_id)
    else:
        product_earning, product_short_link_str, vendor = parse_not_found_product_pk(domain, original_key, request)

    decoded_warning_text = get_warning_text(vendor, request)

    return JSONResponse({
        'product_pk': product_id,
        'product_link': product_link,
        'product_short_link': product_short_link_str,
        'product_liked': product_liked,
        'product_name': product_name,
        'product_earning': product_earning,
        'warning_text': decoded_warning_text
    })

