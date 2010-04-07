from django.conf.urls.defaults import *
from voting.views import vote_on_object
from apparel.models import *
from django.db.models import Q


product_dict = {
    'queryset': Product.objects.all(),
}

manufacturer_dict = {
    'queryset': Manufacturer.objects.all(),
}

like_product_dict = {
    'model': Product,
    'template_object_name': 'product',
    'slug_field': 'slug',
    'allow_xmlhttprequest': True,
}

like_look_dict = {
    'model': Look,
    'template_object_name': 'look',
    'slug_field': 'slug',
    'allow_xmlhttprequest': True,
}

urlpatterns = patterns('',
    (r'^$', 'apparel.views.index'),
    (r'^search$', 'apparel.views.wide_search'),
    (r'^products/$', 'django.views.generic.list_detail.object_list', product_dict),
    (r'^(?P<model>\w+)/search$', 'apparel.views.search'),
    (r'^products/(?P<slug>[\w-]+)/$', 'apparel.views.product_detail'), #'django.views.generic.list_detail.object_detail', product_dict),
    (r'^manufacturers/$', 'django.views.generic.list_detail.object_list', manufacturer_dict),
    (r'^manufacturers/(?P<object_id>\d+)/$', 'django.views.generic.list_detail.object_detail', manufacturer_dict),
    (r'^browse/$', 'apparel.views.browse'),
    
    (r'^wardrobe/add/$', 'apparel.views.wardrobe_add'),

    (r'^likes/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
    (r'^looks/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
    (r'^looks/(?P<slug>[\w-]+)/$', 'apparel.views.look_detail'),
    (r'^looks/(?P<slug>[\w-]+)/edit/$', 'apparel.views.look_edit'),
    (r'^looks/add_product/$', 'apparel.views.add_to_look'),
    (r'^looks/save_product/$', 'apparel.views.save_look_product'),
    (r'^looks/(?P<slug>[\w-]+)/like/(?P<direction>up|clear)/?$', vote_on_object, like_look_dict, "like-look"),
    (r'^products/(?P<slug>[\w-]+)/like/(?P<direction>up|clear)/?$', vote_on_object, like_product_dict, "like-product"),
    (r'^monitor/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
)

