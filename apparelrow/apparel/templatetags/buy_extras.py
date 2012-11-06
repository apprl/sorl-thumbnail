from urlparse import parse_qs, urlsplit, urlunsplit
from urllib import urlencode

from django.template import Library
from django.utils.http import urlquote
from django.core.urlresolvers import reverse

register = Library()


def set_query_parameter(url, param_name, param_value):
    """
    Given a URL, set or replace a query parameter and return the modified
    URL.

    >>> set_query_parameter('http://example.com?foo=bar&biz=baz', 'foo', 'stuff')
    'http://example.com?foo=stuff&biz=baz'

    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)

    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


@register.simple_tag
def buy_url(product_id, vendor, target_user_id='0', page='Default'):
    """
    Append custom SID to every buy URL.
    """
    try:
        sid = int(target_user_id)
    except (TypeError, ValueError, AttributeError):
        sid = 0
    sid = '%s-%s' % (sid, page)

    vendor_feed = vendor.vendor.vendor_feed
    url = vendor.buy_url

    # Tradedoubler
    if vendor_feed.provider_class == 'tradedoubler':
        url = '%sepi(%s)' % (url, sid)
    # Commission Junction
    elif vendor_feed.provider_class == 'cj':
        url = set_query_parameter(url, 'SID', sid)
    # Zanox
    elif vendor_feed.provider_class == 'zanox':
        url = '%s&zpar0=%s' % (url, sid)
    # Linkshare
    elif vendor_feed.provider_class == 'linkshare':
        url = set_query_parameter(url, 'u1', sid)
    # Affiliate Window
    elif vendor_feed.provider_class == 'affiliatewindow':
        url = set_query_parameter(url, 'clickref', sid)

    return '%s?i=%s&u=%s' % (reverse('product-click-count'),
                             product_id,
                             urlquote(url))
