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
    import requests
    from apparelrow.settings import GEOIP_URL
    import logging
    log = logging.getLogger(__name__)
    resp = requests.get(GEOIP_URL % get_client_ip(request))
    json_obj = resp.json()
    if hasattr(json_obj,"iso_code"):
        return json_obj.get("iso_code","ALL")
    else:
        log.warning('No country found for ip %s.' % get_client_ip(request))
        return "ALL"