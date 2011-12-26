from django.conf.urls.defaults import patterns, url

from apparelrow.apparel.models import Look

urlpatterns = patterns('',
    # Index
    url(r'^$', 'apparel.views.gender', {'view': 'index'}, name='index'),
    url(r'^men/$', 'apparel.views.index', {'gender': 'M'}, name='index-men'),
    url(r'^women/$', 'apparel.views.index', {'gender': 'W'}, name='index-women'),

    # Home
    (r'^home/$', 'apparel.views.home'),

    # Products
    (r'^products/(?P<pk>[\d]+)/$', 'apparel.views.product_redirect'),
    (r'^products/(?P<slug>[\w-]+)/$', 'apparel.views.product_detail'),
    url(r'^products/(?P<contains>[\w-]+)/looks/$', 'apparel.views.look_list', name='product-look-list'),
    (r'^products/(?P<slug>[\w-]+?)/(?P<action>like|unlike)/?$', 'apparel.views.product_like'),
    (r'^products/(?P<slug>[\w-]+)/users/$', 'apparel.views.product_user_like_list'),

    # Brand
    url(r'^brands/$', 'apparel.views.gender', {'view': 'brand-list'}, name='brand-list'),
    url(r'^brands/men/$', 'apparel.views.brand_list', {'gender': 'M'}, name='brand-list-men'),
    url(r'^brands/women/$', 'apparel.views.brand_list', {'gender': 'W'}, name='brand-list-women'),

    # Shop
    url(r'^shop/$', 'apparel.views.gender', {'view': 'shop'}, name='shop'),
    url(r'^shop/men/$', 'apparel.browse.browse_products', {'gender': 'M'}, name='shop-men'),
    url(r'^shop/women/$', 'apparel.browse.browse_products', {'gender': 'W'}, name='shop-women'),
    url(r'^shop/men/manufacturers/$', 'apparel.browse.browse_manufacturers', {'gender': 'M'}, name='shop-manufacturers-men'),
    url(r'^shop/women/manufacturers/$', 'apparel.browse.browse_manufacturers', {'gender': 'W'}, name='shop-manufacturers-women'),

    # Wardrobe
    (r'^wardrobe/add_product/$', 'apparel.views.add_to_wardrobe'),
    (r'^wardrobe/delete_product/$', 'apparel.views.delete_from_wardrobe'),

    # Looks
    url(r'^looks/$', 'apparel.views.gender', {'view': 'look-list'}, name='look-list'),
    url(r'^looks/men/$', 'apparel.views.look_list', {'gender': 'M'}, name='look-list-men'),
    url(r'^looks/women/$', 'apparel.views.look_list', {'gender': 'W'}, name='look-list-women'),
    url(r'^looks/popular/$', 'apparel.views.look_list', {'popular': True}, name='popular-look-list'),
    url(r'^looks/search/$', 'apparel.views.look_list', {'search': True}, name='search-look-list'),
    (r'^looks/create/$', 'apparel.views.look_create'),
    (r'^looks/save_component/$', 'apparel.views.save_look_component'),
    (r'^looks/delete_component/$', 'apparel.views.delete_look_component'),
    (r'^looks/add_product/$', 'apparel.views.add_to_look'),
    (r'^looks/(?P<slug>[\w-]+)/$', 'apparel.views.look_detail'),
    (r'^looks/(?P<slug>[\w-]+?)/delete/$', 'apparel.views.look_delete'),
    (r'^looks/(?P<slug>[\w-]+?)/edit/$', 'apparel.views.look_edit'),
    (r'^looks/(?P<slug>[\w-]+?)/(?P<action>like|unlike)/?$', 'apparel.views.look_like'),
    (r'^looks/(?P<slug>[\w-]+)/users/$', 'apparel.views.look_user_like_list'),

    # Dialogs
    url(r'^dialog/login-friends/$', 'apparel.views.dialog_login_favorite_friends', name='dialog-login-friends'),
    url(r'^dialog/like-product/$', 'apparel.views.dialog_like_product', name='dialog-like-product'),
    url(r'^dialog/like-look/$', 'apparel.views.dialog_like_look', name='dialog-like-look'),
    url(r'^dialog/follow-user/$', 'apparel.views.dialog_follow_user', name='dialog-follow-user'),

    # Widget
    url(r'^widget/look/(?P<object_id>\d+)/collage/$', 'apparel.views.widget', {
        'model': Look,
        'template_name': 'apparel/fragments/look_collage.html',
     }),
    url(r'^widget/look/(?P<object_id>\d+)/photo/$', 'apparel.views.widget', {
        'model': Look,
        'template_name': 'apparel/fragments/look_photo.html',
     }),

    # Users
    url(r'^users/$', 'apparel.views.gender', {'view': 'user-list'}, name='user-list'),
    url(r'^users/men/$', 'apparel.views.user_list', {'gender': 'M'}, name='user-list-men'),
    url(r'^users/women/$', 'apparel.views.user_list', {'gender': 'W'}, name='user-list-women'),
    url(r'^users/popular/$', 'apparel.views.gender', {'view': 'user-list-popular'}, name='user-list-popular'),
    url(r'^users/men/popular/$', 'apparel.views.user_list', {'gender': 'M', 'popular': True}, name='user-list-popular-men'),
    url(r'^users/women/popular/$', 'apparel.views.user_list', {'gender': 'W', 'popular': True}, name='user-list-popular-women'),

    # Gender selection
    url(r'^gender/men/$', 'apparel.views.gender', {'gender': 'M'}, name='gender-men'),
    url(r'^gender/women/$', 'apparel.views.gender', {'gender': 'W'}, name='gender-women'),
    url(r'^gender/(?P<view>[\w-]+)/$', 'apparel.views.gender', name='gender'),

    url(r'^monitor/$', 'django.views.generic.simple.direct_to_template', {'template': 'base.html'}),
)


