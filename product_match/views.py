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

logger = logging.getLogger("apparelrow")


# Create your views here.

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


def product_lookup_by_solr(key, fragment=False, vendor_id=None):
    logger.info("Trying to lookup %s from SOLR." % key)

    # Lookup if it is contained if parameter fragment is True
    if fragment:
        try:
            key = str(SQ(product_key=key))
        except:
            key = str(SQ(product_key=key.encode('utf-8')))
        qs = embed_wildcard_solr_query(key)
        kwargs = {'fq': [qs], 'rows': 1, 'django_ct': "apparel.product"}
    else:
        kwargs = {'fq': ['product_key:\"%s\"' % (key,)], 'rows': 1, 'django_ct': "apparel.product"}

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
        product_pk = product_lookup_by_solr(key, True, vendor_id)
        if product_pk:
            return product_pk

    return None
    # json_data = json.loads(products[0].json)
    # return json_data.get('site_product', None)


@csrf_exempt
def product_lookup_multi(request):
    if request.method == "GET":
        raise HttpResponseNotAllowed("Only POST allowed.", permitted_methods=["POST"])

    user_id = request.POST.get("user_id", None)
    if user_id:
        user = User.objects.get(pk=user_id)
        if not user.is_publisher:
            raise Http404

    translated_links = []
    try:
        links = simplejson.loads(request.POST.get("links"))
        for link in links:
            product_short_link_str, vendor = get_short_domain_deeplink(link, link, user_id)
            if product_short_link_str is not None:
                translated_links.append(request.build_absolute_uri(product_short_link_str))
            else:
                translated_links.append(None)
    except JSONDecodeError, msg:
        logger.warn(
            u"Product lookup (wp)service: Unable to decode the links: {}. [{}]".format(msg, request.POST.get("links")))
    except Exception, msg:
        logger.warn(u"Product lookup (wp)service: Unknown error: {}.".format(msg))

    return JSONResponse({"links": translated_links})


def product_lookup(request):
    if not request.user.is_authenticated():
        raise Http404

    key, domain, product_pk, is_nelly_product = extract_product_lookup_parameters(request.GET.copy(),
                                                                                  request.POST.copy())
    original_key = key
    if key and not product_pk:
        product_pk = lookup_product_pk(key, is_nelly_product)
    # TODO: must go through theimp database right now to fetch site product by real url
    # key = smart_unicode(urllib.unquote(smart_str(request.GET.get('key', ''))))
    # imported_product = get_object_or_404(get_model('theimp', 'Product'), key__startswith=key)

    # json_data = json.loads(imported_product.json)
    # product_pk = json_data.get('site_product', None)
    product_link = None
    product_liked = False
    product_name = None
    product_earning = None

    # Only adds approx to earning text when user does not earn CPC for all stores
    approx_text = "approx. "
    if request.user and request.user.partner_group and request.user.partner_group.has_cpc_all_stores:
        approx_text = ""

    vendor = None

    if product_pk:
        product = get_object_or_404(Product, pk=product_pk, published=True)
        product_link = request.build_absolute_uri(product.get_absolute_url())
        product_short_link, created = ShortProductLink.objects.get_or_create(product=product, user=request.user)
        product_short_link_str = reverse('product-short-link', args=[product_short_link.link()])
        product_short_link_str = request.build_absolute_uri(product_short_link_str)
        logger.info(u"Product match found for key, creating short product link [%s]." % product_short_link_str)
        product_liked = get_model('apparel', 'ProductLike').objects.filter(user=request.user, product=product,
                                                                           active=True).exists()
        product_name = product.get_product_name_to_display
        vendor = product.default_vendor.vendor
        earning, currency = product.default_vendor.get_product_earning(request.user)
        if earning and currency:
            help_text = "sale" if vendor.is_cpo else "click"
            product_earning = "You will earn %s%s %s per generated %s of this item." % (
                approx_text, currency, earning, help_text)
    else:
        logger.info(u"No product found for key, falling back to domain deep linking.")
        product_short_link_str, vendor = get_short_domain_deeplink(domain, original_key, request.user.id)
        if product_short_link_str is not None:
            product_short_link_str = request.build_absolute_uri(product_short_link_str)
            _, cut, _, publisher_cut = get_cuts_for_user_and_vendor(request.user.id, vendor)

            if request.user.partner_group and request.user.partner_group.has_cpc_all_stores:
                product_earning = get_product_earning_group(vendor, request.user, publisher_cut, approx_text)
            else:
                product_earning = get_product_earning_standalone(vendor, cut, publisher_cut, approx_text)
        else:
            raise Http404
    vendor_markets = None
    if vendor:
        vendor_markets = vendor.location_codes_list()
    warning_text = get_location_warning_text(vendor_markets, request.user, "chrome-ext")

    return JSONResponse({
        'product_pk': product_pk,
        'product_link': product_link,
        'product_short_link': product_short_link_str,
        'product_liked': product_liked,
        'product_name': product_name,
        'product_earning': product_earning,
        'warning_text': warning_text.decode()
    })


def extract_domain_with_suffix(domain):
    try:
        tld_ext = tldextract.TLDExtract(cache_file=settings.TLDEXTRACT_CACHE)
        extracted = tld_ext(domain)
        return "%s.%s" % (extracted.domain, extracted.suffix)
    except Exception, msg:
        logger.info("Domain supplied could not be extracted: %s [%s]" % (domain, msg))
        return None


# Todo: move this to product manager (also deprecated now since 20151020)
def extract_apparel_product_with_url(key):
    return get_model('apparel', 'Product').objects.filter(published=True, product_key__icontains=key)


def embed_wildcard_solr_query(qs_string):
    return "%s*%s*" % (qs_string[:qs_string.index(':') + 1], qs_string[qs_string.index(':') + 1:])


def extract_encoded_url_string(url):
    try:
        key = smart_unicode(smart_str(url))
    except DjangoUnicodeDecodeError:
        key_string = url.decode("iso-8859-1")
        key = smart_unicode(smart_str(key_string))
    return key


def extract_product_lookup_parameters(GET, POST):
    """
    Takes a request and returns the parameters key, pk, and domain in either GET or POST if available.
    :param request:
    :return:
    """
    # try to get it into unicode
    sent_key = GET.get('key', '') or POST.get('key', '')
    url = extract_encoded_url_string(sent_key)
    # unquote the string, however urrlib doesn't deal with unicode so convert it to utf-8 and back
    key = extract_encoded_url_string(urllib.unquote(url.encode('utf-8')))

    sent_domain = GET.get('domain', '') or POST.get('domain', '')
    domain = smart_unicode(urllib.unquote(smart_str(sent_domain))) or key
    is_nelly_product = bool(GET.get('is_product', False) or POST.get('is_product', False))

    logger.info("Request to lookup product for %s sent, trying to extract PK from request." % key)
    try:
        sent_pk = GET.get('pk', '') or POST.get('pk', '')
        product_pk = long(extract_encoded_url_string(sent_pk))
    except ValueError:
        product_pk = None
        logger.info("No clean Product pk extracted.")
    return key, domain, product_pk, is_nelly_product


def switch_http_protocol(key):
    logger.info("Failed to extract product from solr, will change the protocol and try again.")
    if key.startswith('https'):
        key = key.replace('https', 'http', 1)
    elif key.startswith('http'):
        key = key.replace("http", "https", 1)
    return key


def lookup_product_pk(key, is_nelly_product):
    product_pk = product_lookup_by_solr(key)
    if not product_pk:
        product_pk = product_lookup_by_solr(switch_http_protocol(key))
        if not product_pk:
            logger.info(u"Failed to extract product from solr for %s" % key)
            product_pk = product_lookup_asos_nelly(key, is_nelly_product)
        else:
            logger.info(u"Successfully found product in SOLR for key %s" % key)
    else:
        logger.info("Successfully found product in SOLR for key %s" % key)

    return product_pk


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

    while url_candidate and not product_pk and url_combination_tries_left > 0:
        product_pk = product_lookup_product_id_by_solr(url_candidate)
        if not product_pk:
            url_candidate = switch_url_candidate(url_candidate)
            url_combination_tries_left -= 1
        if product_pk:
            url_combination_tries_left = 0

    return product_pk


def extract_product_lookup_domain(GET, POST, key):
    sent_domain = GET.get('domain', '') or POST.get('domain', '')
    domain = smart_unicode(urllib.unquote(smart_str(sent_domain))) or key
    return domain


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


def lookup_product(request):
    if not request.user.is_authenticated():
        raise Http404

    product_link = None
    product_liked = False
    product_name = None

    original_key, domain = extract_url_and_domain(request)
    url_candidate = remove_query_parameters_from_url(original_key)

    product_pk = try_extract_product_pk(url_candidate)

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


def product_lookup_product_id_by_solr(key):
    logger.info("Trying to lookup %s from SOLR." % key)
    product_id = None

    kwargs = {'fq': ['product_key:\"%s\"' % (key,)], 'rows': 1, 'django_ct': "apparel.product"}
    connection = Solr(settings.SOLR_URL)
    result = connection.search("*", **kwargs)
    dict = result.__dict__

    logger.info("Query executed in %s milliseconds" % dict['qtime'])

    if dict['hits'] < 1:
        logger.info("No results found for key %s." % key)
    else:
        logger.info("%s results found" % dict['hits'])
        product_id = int(dict['docs'][0]['django_id'])
        logger.info("pk from solr %s ." % product_id)

    return product_id