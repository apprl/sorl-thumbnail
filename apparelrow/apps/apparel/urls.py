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
    (r'^products/search$', 'apps.apparel.views.search'),
    (r'^products/(?P<object_id>\d+)/$', 'django.views.generic.list_detail.object_detail', product_dict),
    (r'^manufacturers/$', 'django.views.generic.list_detail.object_list', manufacturer_dict),
    (r'^manufacturers/search$', 'apps.apparel.views.search'),
    (r'^manufacturers/(?P<object_id>\d+)/$', 'django.views.generic.list_detail.object_detail', manufacturer_dict),
    (r'^categories/search$', 'apps.apparel.views.search'),
    (r'^vendors/search$', 'apps.apparel.views.search'),
    (r'^filter/$', 'apps.apparel.views.filter'),

    (r'^likes/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
    (r'^looks/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
    (r'^monitor/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
)

