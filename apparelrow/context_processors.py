import logging
from apparel.views import js_template, get_template_source
from django.conf import settings as django_settings


def cache_vars(request):
    return {
        'CACHE_TIMEOUT': django_settings.CACHE_TEMPLATE_TIMEOUT
    }

def js_templates(request):    
    return {
        'default_templates': {
            'product': js_template(get_template_source('apparel/fragments/product_small.html'), context=RequestContext(request)),
            #'look_search': get_template_source('apparel/fragments/look_search.html'),
            #'manufacturer_search': js_template(get_template_source('apparel/fragments/manufacturer_search.html')),
        },
    }
