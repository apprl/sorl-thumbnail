from django.conf.urls.defaults import *
from voting.views import vote_on_object
from apparel.models import *
from django.db.models import Q


# FIXME: There's currently no way for django-voting to limit the Product queryset
# to only contain published products
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
    (r'^(?P<model>\w+)/search$', 'apparel.views.search'),
    (r'^products/(?P<pk>[\d]+)/$', 'apparel.views.product_redirect'),
    (r'^products/(?P<slug>[\w-]+)/$', 'apparel.views.product_detail'),
    (r'^products/(?P<contains>[\w-]+)/looks/$', 'apparel.views.look_list'),
    (r'^products/(?P<slug>[\w-]+?)/like/(?P<direction>up|clear)/?$', vote_on_object, like_product_dict, "like-product"),
    
    (r'^browse/$', 'apparel.views.browse'),
    
    (r'^wardrobe/add_product/$', 'apparel.views.add_to_wardrobe'),

    (r'^looks/$', 'apparel.views.look_list'),
    (r'^looks/create/$', 'apparel.views.look_create'),
    (r'^looks/save_component/$', 'apparel.views.save_look_component'),
    (r'^looks/delete_component/$', 'apparel.views.delete_look_component'),
    (r'^looks/add_product/$', 'apparel.views.add_to_look'),
    (r'^looks/(?P<slug>[\w-]+)/$', 'apparel.views.look_detail'),
    (r'^looks/(?P<slug>[\w-]+?)/edit/$', 'apparel.views.look_edit'),
    (r'^looks/(?P<slug>[\w-]+?)/like/(?P<direction>up|clear)/?$', vote_on_object, like_look_dict, "like-look"),
    (r'^monitor/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
    
    (r'^widget/look/(?P<object_id>\d+)/collage/$', 'apparel.views.widget', { 
        'model': Look,
        'template_name': 'apparel/fragments/look_collage.html',
     }),
    (r'^widget/look/(?P<object_id>\d+)/photo/$', 'apparel.views.widget', { 
        'model': Look,
        'template_name': 'apparel/fragments/look_photo.html',
     }),
)


