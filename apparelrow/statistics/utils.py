import requests
from requests import Timeout
from django.conf import settings
import logging

log = logging.getLogger("apparelrow")

def get_client_referer(request, default=None):
    referer = request.META.get('HTTP_REFERER')
    if not referer:
        return default

    return referer

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    return ip


def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')


def get_country_by_ip(request):
    return get_country_by_ip_string(get_client_ip(request))

def get_country_by_ip_string(ip_string):
    """
    Takes ip and does a lookup against the ip-service.
    If the Country code returned is not defined as a specific country for which we have a market specified, the function
    will return ALL.
    :param ip_string: Ip of the client
    :return: The country code returned from the service or ALL which implies all markets.
    """

    if settings.GEOIP_DEBUG:
        return settings.GEOIP_RETURN_LOCATION
    json_obj = None

    try:
        resp = requests.get(settings.GEOIP_URL % ip_string,timeout=1.0)
        json_obj = resp.json()
    except Timeout, msg:
        log.warning('Timeout occurred in geoip lookup function. > 1000ms response time. Service down? [%s]' % msg)
    except Exception, msg:
        log.warning('Reply from geoip service not complient with json? [%s]' % msg)

    if json_obj and json_obj.get("iso_code",None):
        code = json_obj.get("iso_code","ALL")
        code = code if code in ["SE", "NO", "US", "DK", "FI"] else "ALL"
        return code
    else:
        log.info('No country found for ip %s.' % ip_string)
        return "ALL"

def extract_short_link_from_url(parsed_url, user_id=None):
    """
    Gets the short code from parsed url, works regardless of locale redirects are in function
    :param parsed_url: full url userid included
    :param user_id: if user id is supplied in the url
    :return: short url code
    """
    if not user_id:
        if parsed_url.endswith("/"):
            return parsed_url.split("/")[-2]
        else:
            return parsed_url.split("/")[-1]

    else:
        if parsed_url.endswith("/"):
            return parsed_url.split("/")[-3]
        else:
            return parsed_url.split("/")[-2]
