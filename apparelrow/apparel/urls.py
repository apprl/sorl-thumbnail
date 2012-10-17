from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from apparel.models import Look

urlpatterns = patterns('',
    # Feed
    url(r'^all/$', 'activity_feed.views.public_feed', name='public_feed'),
    url(r'^$', 'activity_feed.views.user_feed', name='user_feed'),

    # Shop
    url(r'^shop/$', 'apparel.views.gender', {'view': 'shop'}, name='shop'),
    url(r'^shop/men/$', 'apparel.browse.browse_products', {'gender': 'M'}, name='shop-men'),
    url(r'^shop/women/$', 'apparel.browse.browse_products', {'gender': 'W'}, name='shop-women'),

    # About
    url(r'^about/$', 'apparel.views.about', name='about'),

    # Facebook friends widget
    (r'^home/friends/$', 'apparel.views.facebook_friends_widget'),

    # Search
    (r'^search/(?P<model_name>\w+)/', 'apparel.search.search_view'),

    # Notifications
    url(r'^notification/like_product/$', 'apparel.views.notification_like_product', name='notification-like-product'),
    url(r'^notification/like_look/$', 'apparel.views.notification_like_look', name='notification-like-look'),
    url(r'^notification/create_look/$', 'apparel.views.notification_create_look', name='notification-create-look'),
    url(r'^notification/follow_member/$', 'apparel.views.notification_follow_member', name='notification-follow-member'),
    url(r'^notification/follow_brand/$', 'apparel.views.notification_follow_brand', name='notification-follow-brand'),

    # Facebook
    url(r'^facebook/share/(?P<activity>push|pull)/?$', 'apparel.views.facebook_share', name='facebook-share'),

    # Follow/Unfollow API
    url(r'^follow/(?P<profile_id>\d+)/$', 'apparel.views.follow_unfollow', name='apprl-follow'),
    url(r'^unfollow/(?P<profile_id>\d+)/$', 'apparel.views.follow_unfollow', {'do_follow': False}, name='apprl-unfollow'),

    # Products
    (r'^products/(?P<pk>[\d]+)/$', 'apparel.views.product_redirect'),
    url(r'^products/(?P<pk>[\d]+)/(?P<action>like|unlike)/?$', 'apparel.views.product_action', name='product-action'),
    (r'^products/(?P<slug>[\w-]+)/$', 'apparel.views.product_detail'),
    url(r'^products/(?P<contains>[\w-]+)/looks/$', 'apparel.views.look_list', name='product-look-list'),
    (r'^products/(?P<slug>[\w-]+?)/(?P<action>like|unlike)/?$', 'apparel.views.product_like'),

    # Brand
    url(r'^brands/(?P<pk>[\d]+)/$', 'apparel.views.brand_redirect', name='brand-redirect'),
    url(r'^brands/$', 'apparel.views.gender', {'view': 'brand-list'}, name='brand-list'),
    url(r'^brands/men/$', 'apparel.views.brand_list', {'gender': 'M'}, name='brand-list-men'),
    url(r'^brands/women/$', 'apparel.views.brand_list', {'gender': 'W'}, name='brand-list-women'),
    url(r'^brands/popular/$', 'apparel.views.gender', {'view': 'brand-list-popular'}, name='brand-list-popular'),
    url(r'^brands/popular/men/$', 'apparel.views.brand_list', {'gender': 'M', 'popular': True}, name='brand-list-popular-men'),
    url(r'^brands/popular/women/$', 'apparel.views.brand_list', {'gender': 'W', 'popular': True}, name='brand-list-popular-women'),

    # Brand profile
    url(r'^brand/(?:([^\/]+?)/)?$', 'apparel.views.gender', {'view': 'brand-likes'}, name='brand-likes'),
    url(r'^brand/(?:([^\/]+?)/)?men/$', 'profile.views.likes', {'gender': 'M'}, name='brand-likes-men'),
    url(r'^brand/(?:([^\/]+?)/)?women/$', 'profile.views.likes', {'gender': 'W'}, name='brand-likes-women'),
    url(r'^brand/(?:([^\/]+?)/)?updates/$', 'profile.views.profile', name='brand-updates'),
    url(r'^brand/(?:([^\/]+?)/)?looks/$', 'profile.views.looks', name='brand-looks'),
    url(r'^brand/(?:([^\/]+?)/)?followers/$', 'profile.views.followers', name='brand-followers'),
    url(r'^brand/(?:([^\/]+?)/)?following/$', 'profile.views.following', name='brand-following'),

    # Shop
    url(r'^shop/popup/$', 'apparel.views.product_popup', name='product-popup'),

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

    # Dialogs
    url(r'^dialog/login-friends/$', 'apparel.views.dialog_login_favorite_friends', name='dialog-login-friends'),
    url(r'^dialog/like-product/$', 'apparel.views.dialog_like_product', name='dialog-like-product'),
    url(r'^dialog/like-look/$', 'apparel.views.dialog_like_look', name='dialog-like-look'),
    url(r'^dialog/follow-user/$', 'apparel.views.dialog_follow_user', name='dialog-follow-user'),
    url(r'^dialog/why-facebook$', TemplateView.as_view(template_name='apparel/fragments/dialog_why_facebook.html'), name='dialog-why-facebook'),
    url(r'^dialog/user-feed/$', 'activity_feed.views.dialog_user_feed', name='dialog-user-feed'),

    # Embed
    url(r'^embed/look/(?P<slug>[\w-]+)/$', 'apparel.views.look_embed'),

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
    url(r'^users/$', 'apparel.views.user_list', name='user-list'),
    url(r'^users/men/$', 'apparel.views.user_list', {'view_gender': 'M'}, name='user-list-men'),
    url(r'^users/women/$', 'apparel.views.user_list', {'view_gender': 'W'}, name='user-list-women'),
    url(r'^users/popular/$', 'apparel.views.user_list', {'popular': True }, name='user-list-popular'),
    url(r'^users/men/popular/$', 'apparel.views.user_list', {'view_gender': 'M', 'popular': True}, name='user-list-popular-men'),
    url(r'^users/women/popular/$', 'apparel.views.user_list', {'view_gender': 'W', 'popular': True}, name='user-list-popular-women'),

    # Gender selection
    url(r'^gender/change/$', 'apparel.views.change_gender', name='change-gender'),
    url(r'^gender/men/$', 'apparel.views.gender', {'gender': 'M'}, name='gender-men'),
    url(r'^gender/women/$', 'apparel.views.gender', {'gender': 'W'}, name='gender-women'),
    url(r'^gender/(?P<view>[\w-]+)/$', 'apparel.views.gender', name='gender'),

    # Jobs
    url(r'^jobs/$', 'apparel.views.jobs', name='jobs'),

    # Mailchimp - email
    url(r'^admin/csv/users/$', 'apparel.email.admin_user_list_csv'),
    url(r'^admin/mail/weekly/$', 'apparel.email.generate_weekly_mail'),
    url(r'^admin/mailchimp/webhook/$', 'apparel.email.mailchimp_webhook'),
)


