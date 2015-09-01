from requests import Timeout


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
    json_obj = None
    try:
        resp = requests.get(GEOIP_URL % get_client_ip(request),timeout=0.5)
        json_obj = resp.json()
    except Timeout,msg:
        log.warning('Timeout occurred in geoip lookup function. > 500ms response time. Service down? [%s]' % msg)
    except Exception,msg:
        log.warning('Reply from geoip service not complient with json? [%s]' % msg)

    if json_obj and json_obj.get("iso_code",None):
        code = json_obj.get("iso_code","ALL")
        code = code if code in ["SE","NO","US"] else "ALL"
        return code
    else:
        log.info('No country found for ip %s.' % get_client_ip(request))
        return "ALL"

def get_country_by_ip_string(ip):
    import requests
    from apparelrow.settings import GEOIP_URL
    import logging
    log = logging.getLogger(__name__)
    json_obj = None
    try:
        resp = requests.get(GEOIP_URL % ip,timeout=0.5)
        json_obj = resp.json()
    except Timeout,msg:
        log.warning('Timeout occurred in geoip lookup function. > 500ms response time. Service down? [%s]' % msg)
    except Exception,msg:
        log.warning('Reply from geoip service not complient with json? [%s]' % msg)

    if json_obj and json_obj.get("iso_code",None):
        code = json_obj.get("iso_code","ALL")
        code = code if code in ["SE","NO","US"] else "ALL"
        return code
    else:
        log.info('No country found for ip %s.' % ip)
        return "ALL"