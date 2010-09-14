import logging
from apparel.views import js_template, get_template_source
from django.conf import settings as django_settings

def settings(request):
    return {'django_settings': django_settings }


def js_templates(request):
    # FIXME: Move the js_template and get_template_source to a utilities library
    
    return {
        'default_templates': {
            'product': js_template(get_template_source('apparel/fragments/product_small.html')),
            'look_search': get_template_source('apparel/fragments/look_search.html'),
            'manufacturer_search': js_template(get_template_source('apparel/fragments/manufacturer_search.html')),
        },
    }
