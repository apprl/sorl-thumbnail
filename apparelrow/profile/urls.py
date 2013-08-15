from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

urlpatterns = patterns('',
    url(r'^flow/$', 'apparelrow.profile.views.flow', name='login-flow-redirect'),
    url(r'^embed/shop/$', 'apparelrow.profile.views.embed_shop', name='profile-embed-shop'),
    url(r'^settings/$', 'apparelrow.profile.views.settings_notification', name='settings'),
    url(r'^settings/notification/$', 'apparelrow.profile.views.settings_notification', name='settings-notification'),
    url(r'^settings/email/$', 'apparelrow.profile.views.settings_email', name='settings-email'),
    url(r'^settings/facebook/$', 'apparelrow.profile.views.settings_facebook', name='settings-facebook'),
    url(r'^settings/partner/$', 'apparelrow.profile.views.settings_partner', name='settings-partner'),
    url(r'^settings/password/$', 'apparelrow.profile.views.settings_password', name='settings-password'),
    url(r'^settings/description/$', 'apparelrow.profile.views.save_description', name='settings-save-description'),
    url(r'^confirm/email/$', 'apparelrow.profile.views.confirm_email', name='user-confirm-email'),
    url(r'^welcome/friends/$', 'apparelrow.profile.views.login_flow_friends', name='login-flow-friends'),
    url(r'^welcome/featured/$', 'apparelrow.profile.views.login_flow_featured', name='login-flow-featured'),
    url(r'^welcome/brands/$', 'apparelrow.profile.views.login_flow_brands', name='login-flow-brands'),
    url(r'^welcome/complete/$', 'apparelrow.profile.views.login_flow_complete', name='login-flow-complete'),
    url(r'^(?:([^\/]+?)/)?$', 'apparelrow.profile.views.likes', name='profile-likes'),
    url(r'^(?:([^\/]+?)/)?updates/$', RedirectView.as_view(url=reverse_lazy('profile-likes')), name='redirect-profile-updates'),
    url(r'^(?:([^\/]+?)/)?looks/$', 'apparelrow.profile.views.looks', name='profile-looks'),
    url(r'^(?:([^\/]+?)/)?followers/$', 'apparelrow.profile.views.followers', name='profile-followers'),
    url(r'^(?:([^\/]+?)/)?following/$', 'apparelrow.profile.views.following', name='profile-following'),
)

