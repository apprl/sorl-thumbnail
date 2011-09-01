from django.conf.urls.defaults import patterns, url

from apparelrow.apparel.models import Look

urlpatterns = patterns('',
    (r'^$', 'apparel.views.index'),
    (r'^home/$', 'apparel.views.home'),
    (r'^(?P<model>\w+)/search$', 'apparelrow.search.search_view'),
    (r'^products/(?P<pk>[\d]+)/$', 'apparel.views.product_redirect'),
    (r'^products/(?P<slug>[\w-]+)/$', 'apparel.views.product_detail'),
    url(r'^products/(?P<contains>[\w-]+)/looks/$', 'apparel.views.look_list', name='product-look-list'),
    (r'^products/(?P<slug>[\w-]+?)/(?P<action>like|unlike)/?$', 'apparel.views.product_like'),
    (r'^products/(?P<slug>[\w-]+)/users/$', 'apparel.views.product_user_like_list'),
    
    (r'^browse/$', 'apparel.browse.browse_products'),
    (r'^browse/manufacturers/$', 'apparel.browse.browse_manufacturers'),
    
    (r'^wardrobe/add_product/$', 'apparel.views.add_to_wardrobe'),
    (r'^wardrobe/delete_product/$', 'apparel.views.delete_from_wardrobe'),

    url(r'^looks/$', 'apparel.views.look_list', name='look-list'),
    url(r'^looks/popular/$', 'apparel.views.look_list', {'popular': True}, name='popular-look-list'),
    (r'^looks/create/$', 'apparel.views.look_create'),
    (r'^looks/save_component/$', 'apparel.views.save_look_component'),
    (r'^looks/delete_component/$', 'apparel.views.delete_look_component'),
    (r'^looks/add_product/$', 'apparel.views.add_to_look'),
    (r'^looks/(?P<slug>[\w-]+)/$', 'apparel.views.look_detail'),
    (r'^looks/(?P<slug>[\w-]+?)/delete/$', 'apparel.views.look_delete'),
    (r'^looks/(?P<slug>[\w-]+?)/edit/$', 'apparel.views.look_edit'),
    (r'^looks/(?P<slug>[\w-]+?)/(?P<action>like|unlike)/?$', 'apparel.views.look_like'),
    (r'^looks/(?P<slug>[\w-]+)/users/$', 'apparel.views.look_user_like_list'),

    url(r'^dialog/login-friends/$', 'apparel.views.dialog_login_favorite_friends', name='dialog-login-friends'),
    url(r'^dialog/like-product/$', 'apparel.views.dialog_like_product', name='dialog-like-product'),
    url(r'^dialog/like-look/$', 'apparel.views.dialog_like_look', name='dialog-like-look'),
    url(r'^dialog/follow-user/$', 'apparel.views.dialog_follow_user', name='dialog-follow-user'),

    (r'^monitor/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
    
    (r'^widget/look/(?P<object_id>\d+)/collage/$', 'apparel.views.widget', { 
        'model': Look,
        'template_name': 'apparel/fragments/look_collage.html',
     }),
    (r'^widget/look/(?P<object_id>\d+)/photo/$', 'apparel.views.widget', { 
        'model': Look,
        'template_name': 'apparel/fragments/look_photo.html',
     }),

    url(r'^users/$', 'apparel.views.user_list', name='user-list'),
    url(r'^users/popular/$', 'apparel.views.user_list', {'popular': True}, name='popular-user-list'),
)


