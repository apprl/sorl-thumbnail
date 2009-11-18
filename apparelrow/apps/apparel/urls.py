from django.conf.urls.defaults import *
from apparel.models import *
from django.db.models import Q


product_dict = {
    'queryset': Product.objects.all(),
}

manufacturer_dict = {
    'queryset': Manufacturer.objects.all(),
}



urlpatterns = patterns('',
    (r'^search$', 'apps.apparel.views.wide_search'),
    (r'^products/$', 'django.views.generic.list_detail.object_list', product_dict),
    (r'^(?P<model>\w+)/search$', 'apps.apparel.views.search'),
    (r'^products/(?P<product_id>\d+)/$', 'apps.apparel.views.product_detail'), #'django.views.generic.list_detail.object_detail', product_dict),
    (r'^manufacturers/$', 'django.views.generic.list_detail.object_list', manufacturer_dict),
    (r'^manufacturers/(?P<object_id>\d+)/$', 'django.views.generic.list_detail.object_detail', manufacturer_dict),
    (r'^filter/$', 'apps.apparel.views.filter'),

    (r'^likes/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
    (r'^looks/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
    (r'^looks/add_product/$', 'apps.apparel.views.add_to_look'),
    (r'^looks/(?P<look_id>\d+)/$', 'apps.apparel.views.look_detail'),
    (r'^monitor/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
)

