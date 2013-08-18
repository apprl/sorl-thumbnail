from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import TemplateView, RedirectView

from apparelrow.apparel.views.products import ProductList
from apparelrow.apparel.views.images import TemporaryImageView
from apparelrow.apparel.views.looks import LookView

urlpatterns = patterns('',
    # Index
    url(r'^$', 'apparelrow.apparel.views.index', name='index'),
    url(r'^store/$', 'apparelrow.apparel.views.store', name='index-store'),

    # Feed
    url(r'^feed/$', 'apparelrow.activity_feed.views.user_feed', name='user_feed'),
    url(r'^all/$', 'apparelrow.activity_feed.views.public_feed', name='public_feed'),
    url(r'^all/men/$', 'apparelrow.activity_feed.views.public_feed', {'gender': 'M'}, name='public_feed-men'),
    url(r'^all/women/$', 'apparelrow.activity_feed.views.public_feed', {'gender': 'W'}, name='public_feed-women'),

    # Shop
    url(r'^shop/$', 'apparelrow.apparel.views.gender', {'view': 'shop'}, name='shop'),
    url(r'^shop/men/$', 'apparelrow.apparel.browse.browse_products', {'gender': 'M'}, name='shop-men'),
    url(r'^shop/women/$', 'apparelrow.apparel.browse.browse_products', {'gender': 'W'}, name='shop-women'),

    # Shop embed - wardrobe
    url(r'^embed/shop/(?P<user_id>\d+)/(?P<language>\w+)/(?P<gender>\w+)/$', 'apparelrow.apparel.browse.shop_embed', name='shop-embed'),
    url(r'^widget/shop/$', 'apparelrow.apparel.browse.shop_widget', name='shop-widget'),

    # About
    url(r'^about/$', 'apparelrow.apparel.views.about', name='about'),

    # Facebook friends widget
    (r'^home/friends/$', 'apparelrow.apparel.views.facebook_friends_widget'),

    # Search
    url(r'^search/$', 'apparelrow.apparel.search.search', name='search'),
    (r'^search/(?P<model_name>\w+)/', 'apparelrow.apparel.search.search_view'),

    # Notifications
    url(r'^notification/like_product/$', 'apparelrow.apparel.views.notification_like_product', name='notification-like-product'),
    url(r'^notification/like_look/$', 'apparelrow.apparel.views.notification_like_look', name='notification-like-look'),
    url(r'^notification/create_look/$', 'apparelrow.apparel.views.notification_create_look', name='notification-create-look'),
    url(r'^notification/follow_member/$', 'apparelrow.apparel.views.notification_follow_member', name='notification-follow-member'),
    url(r'^notification/follow_brand/$', 'apparelrow.apparel.views.notification_follow_brand', name='notification-follow-brand'),

    # Facebook
    url(r'^facebook/share/(?P<activity>push|pull)/?$', 'apparelrow.apparel.views.facebook_share', name='facebook-share'),

    # Follow/Unfollow API
    url(r'^follow/(?P<profile_id>\d+)/$', 'apparelrow.apparel.views.follow_unfollow', name='follow'),
    url(r'^unfollow/(?P<profile_id>\d+)/$', 'apparelrow.apparel.views.follow_unfollow', {'do_follow': False}, name='unfollow'),

    # Temporary Images
    url(r'^images/temporary/$', TemporaryImageView.as_view(), name='temporary-image'),
    url(r'^images/temporary/(?P<pk>[\d]+)/$', TemporaryImageView.as_view(), name='temporary-image-delete'),

    # Products
    url(r'^products/$', ProductList.as_view(), name='product_list'),
    url(r'^products/(?P<pk>[\d]+)/$', 'apparelrow.apparel.views.product_redirect_by_id', name='product-redirect-by-id'),
    url(r'^products/(?P<pk>[\wd]+)/popup/$', 'apparelrow.apparel.views.products.product_detail_popup', name='product-detail-popup'),
    url(r'^products/(?P<pk>[\d]+)/(?P<action>like|unlike)/?$', 'apparelrow.apparel.views.product_action', name='product-action'),
    url(r'^products/(?P<slug>[\w-]+)/$', 'apparelrow.apparel.views.product_detail', name='product-detail'),
    url(r'^products/(?P<slug>[\w-]+)/short/$', 'apparelrow.apparel.views.product_generate_short_link', name='product-generate-short-link'),
    url(r'^products/(?P<contains>[\w-]+)/looks/$', 'apparelrow.apparel.views.look_list', name='product-look-list'),
    url(r'^products/(?P<slug>[\w-]+?)/(?P<action>like|unlike)/?$', 'apparelrow.apparel.views.product_like', name='product-like'),

    # Track product
    url(r'^redirect/(?P<pk>[\d]+)/$', 'apparelrow.apparel.views.product_redirect', name='product-redirect'),
    url(r'^redirect/(?P<pk>[\d]+)/(?P<page>[\w-]+)/(?P<sid>[\d]+)/$', 'apparelrow.apparel.views.product_redirect', name='product-redirect'),
    url(r'^track/(?P<pk>[\d]+)/(?P<page>[\w-]+)/(?P<sid>[\d]+)/$', 'apparelrow.apparel.views.product_track', name='product-track'),

    # Short product link
    url(r'^p/(?P<short_link>[\w]+)/$', 'apparelrow.apparel.views.product_short_link', name='product-short-link'),

    # Brand
    url(r'^brands/(?P<pk>[\d]+)/$', 'apparelrow.apparel.views.brand_redirect', name='brand-redirect'),
    url(r'^brands/$', 'apparelrow.apparel.views.gender', {'view': 'brand-list'}, name='brand-list'),
    url(r'^brands/men/$', 'apparelrow.apparel.views.user_list', {'gender': 'M', 'brand': True}, name='brand-list-men'),
    url(r'^brands/women/$', 'apparelrow.apparel.views.user_list', {'gender': 'W', 'brand': True}, name='brand-list-women'),

    # Brand profile
    url(r'^brand/(?:([^\/]+?)/)?$', 'apparelrow.apparel.views.gender', {'view': 'brand-likes'}, name='brand-likes'),
    url(r'^brand/(?:([^\/]+?)/)?men/$', 'apparelrow.profile.views.likes', {'gender': 'M'}, name='brand-likes-men'),
    url(r'^brand/(?:([^\/]+?)/)?women/$', 'apparelrow.profile.views.likes', {'gender': 'W'}, name='brand-likes-women'),
    url(r'^brand/(?:([^\/]+?)/)?updates/$', RedirectView.as_view(url=reverse_lazy('brand-likes')), name='redirect-brand-updates'),
    url(r'^brand/(?:([^\/]+?)/)?looks/$', 'apparelrow.profile.views.looks', name='brand-looks'),
    url(r'^brand/(?:([^\/]+?)/)?followers/$', 'apparelrow.profile.views.followers', name='brand-followers'),
    url(r'^brand/(?:([^\/]+?)/)?following/$', 'apparelrow.profile.views.following', name='brand-following'),

    # Look / Product popup
    url(r'^popup/product/$', 'apparelrow.apparel.views.product_popup', name='product-popup'),
    url(r'^popup/look/$', 'apparelrow.apparel.views.look_popup', name='look-popup'),

    # Follow backend
    url(r'^backend/follow/$', 'apparelrow.apparel.views.follow_backend', name='follow-backend'),

    # Looks
    url(r'^looks/create/$', 'apparelrow.apparel.views.looks.create', name='look-create'),
    url(r'^looks/create/(?P<slug>[\w-]+)/$', 'apparelrow.apparel.views.looks.create_and_like', name='look-create-like'),
    url(r'^looks/editor/(?P<component>photo|collage)/$', 'apparelrow.apparel.views.looks.editor', name='look-editor'),
    url(r'^looks/editor/(?P<slug>[\w-]+)/$', 'apparelrow.apparel.views.looks.editor', name='look-editor'),

    url(r'^look/$', LookView.as_view(), name='look_list'),
    url(r'^look/(?P<pk>\d+)/?$', LookView.as_view(), name='look'),

    url(r'^looks/$', 'apparelrow.apparel.views.gender', {'view': 'look-list'}, name='look-list'),
    url(r'^looks/men/$', 'apparelrow.apparel.views.look_list', {'gender': 'M'}, name='look-list-men'),
    url(r'^looks/women/$', 'apparelrow.apparel.views.look_list', {'gender': 'W'}, name='look-list-women'),
    url(r'^looks/popular/$', 'apparelrow.apparel.views.look_list', {'popular': True}, name='popular-look-list'),
    url(r'^looks/search/$', 'apparelrow.apparel.views.look_list', {'search': True}, name='search-look-list'),
    url(r'^looks/(?P<slug>[\w-]+)/publish/$', 'apparelrow.apparel.views.looks.publish', name='look-publish'),
    url(r'^looks/(?P<slug>[\w-]+)/unpublish/$', 'apparelrow.apparel.views.looks.unpublish', name='look-unpublish'),
    url(r'^looks/(?P<slug>[\w-]+)/$', 'apparelrow.apparel.views.look_detail', name='look-detail'),
    url(r'^looks/(?P<slug>[\w-]+?)/delete/$', 'apparelrow.apparel.views.look_delete', name='look-delete'),
    url(r'^looks/(?P<slug>[\w-]+?)/(?P<action>like|unlike)/?$', 'apparelrow.apparel.views.look_like', name='look-like'),

    # Look embed + dialog + widget
    url(r'^embed/look/(?P<slug>[\w-]+)/$', 'apparelrow.apparel.views.looks.embed', name='look-embed'),
    url(r'^embed/look/(?P<identifier>\w+)/(?P<slug>[\w-]+)/$', 'apparelrow.apparel.views.looks.embed', name='look-embed-identifier'),
    url(r'^dialog/embed/look/(?P<slug>[\w-]+)/$', 'apparelrow.apparel.views.looks.dialog_embed', name='dialog-look-embed'),
    url(r'^widget/look/(?P<slug>[\w-]+)/$', 'apparelrow.apparel.views.looks.widget', name='look-widget'),

    # Users
    url(r'^users/$', 'apparelrow.apparel.views.gender', {'view': 'user-list'}, name='user-list'),
    url(r'^users/men/$', 'apparelrow.apparel.views.user_list', {'gender': 'M', 'brand': False}, name='user-list-men'),
    url(r'^users/women/$', 'apparelrow.apparel.views.user_list', {'gender': 'W', 'brand': False}, name='user-list-women'),
    url(r'^users/popular/$', RedirectView.as_view(url=reverse_lazy('user-list')), name='user-list-popular'),
    url(r'^users/men/popular/$', RedirectView.as_view(url=reverse_lazy('user-list')), name='user-list-popular-men'),
    url(r'^users/women/popular/$', RedirectView.as_view(url=reverse_lazy('user-list')), name='user-list-popular-women'),

    # Gender selection
    url(r'^gender/change/$', 'apparelrow.apparel.views.change_gender', name='change-gender'),
    url(r'^gender/men/$', 'apparelrow.apparel.views.gender', {'gender': 'M'}, name='gender-men'),
    url(r'^gender/women/$', 'apparelrow.apparel.views.gender', {'gender': 'W'}, name='gender-women'),
    url(r'^gender/(?P<view>[\w-]+)/$', 'apparelrow.apparel.views.gender', name='gender'),

    # Jobs
    url(r'^jobs/$', 'apparelrow.apparel.views.jobs', name='jobs'),

    # Mailchimp - email
    url(r'^admin/csv/users/$', 'apparelrow.apparel.email.admin_user_list_csv'),
    url(r'^admin/mail/weekly/$', 'apparelrow.apparel.email.generate_weekly_mail'),
    url(r'^admin/mailchimp/webhook/$', 'apparelrow.apparel.email.mailchimp_webhook'),
    url(r'^admin/mail/custom/$', 'apparelrow.apparel.views.custom_email.admin', name='custom-email-admin'),
)


