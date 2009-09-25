from django.conf.urls.defaults import *
from apparel.models import *
from django.db.models import Q


product_dict = {
    'queryset': Product.objects.all(),
}

manufacturer_dict = {
    'queryset': Manufacturer.objects.all(),
}

test_dict = {
    'queryset': Product.objects.filter(Q(category__name__icontains='jeans') & Q(Q(options__value__iexact='f') & Q(options__option_type__name__iexact='gender')|Q(options__value__iexact='m') & Q(options__option_type__name__iexact='gender')))
#    'queryset': Product.objects.filter(manufacturer__name__icontains='acne').filter(Q(options__value__iexact='blue') & Q(options__option_type__name__iexact='color'))
}



urlpatterns = patterns('',
    (r'^products/$', 'django.views.generic.list_detail.object_list', product_dict),
    (r'^products/search$', 'apps.apparel.views.search_product'),
    (r'^products/test$', 'django.views.generic.list_detail.object_list', test_dict),
    (r'^products/(?P<object_id>\d+)/$', 'django.views.generic.list_detail.object_detail', product_dict),
    (r'^manufacturers/$', 'django.views.generic.list_detail.object_list', manufacturer_dict),
    (r'^manufacturers/(?P<object_id>\d+)/$', 'django.views.generic.list_detail.object_detail', manufacturer_dict),

    (r'^likes/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
    (r'^looks/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
    (r'^monitor/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
)

