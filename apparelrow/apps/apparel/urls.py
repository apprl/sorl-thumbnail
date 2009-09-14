from django.conf.urls.defaults import *
from apparel.models import *

product_dict = {
    'queryset': Product.objects.all(),
}

manufacturer_dict = {
    'queryset': Manufacturer.objects.all(),
}

urlpatterns = patterns('',
    (r'^products/$', 'django.views.generic.list_detail.object_list', product_dict),
    (r'^products/(?P<object_id>\d+)/$', 'django.views.generic.list_detail.object_detail', product_dict),
    (r'^manufacturers/$', 'django.views.generic.list_detail.object_list', manufacturer_dict),
    (r'^manufacturers/(?P<object_id>\d+)/$', 'django.views.generic.list_detail.object_detail', manufacturer_dict),
)
