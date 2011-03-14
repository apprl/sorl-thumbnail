import logging
from apparel.views import js_template, get_template_source
from django.conf import settings as django_settings

def exposed_settings(request):
    return {
        'CACHE_TIMEOUT': django_settings.CACHE_TEMPLATE_TIMEOUT,
        'DEFAULT_AVATAR': django_settings.APPAREL_DEFAULT_AVATAR,
        'DEFAULT_AVATAR_LARGE': django_settings.APPAREL_DEFAULT_AVATAR_LARGE,
        'GOOGLE_ANALYTICS_ACCOUNT': django_settings.GOOGLE_ANALYTICS_ACCOUNT,
        'GOOGLE_ANALYTICS_DOMAIN': django_settings.GOOGLE_ANALYTICS_DOMAIN,
    }

def js_templates(request):
    return {
        'default_templates': {
            'product': js_template(get_template_source('apparel/fragments/product_small.html'), context=RequestContext(request)),
            #'look_search': get_template_source('apparel/fragments/look_search.html'),
            #'manufacturer_search': js_template(get_template_source('apparel/fragments/manufacturer_search.html')),
        },
    }
