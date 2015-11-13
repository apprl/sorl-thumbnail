from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

urlpatterns = patterns('',
    url(r'^flow/$', 'apparelrow.profile.views.flow', name='login-flow-redirect'),
    url(r'^settings/$', 'apparelrow.profile.views.settings_email', name='settings'),
    url(r'^notifications/$', 'apparelrow.profile.views.notifications', name='notifications-page'),
    url(r'^settings/notification/$', 'apparelrow.profile.views.settings_notification', name='settings-notification'),
    url(r'^settings/email/$', 'apparelrow.profile.views.settings_email', name='settings-email'),
    url(r'^settings/password/$', 'apparelrow.profile.views.settings_password', name='settings-password'),
    url(r'^settings/publisher/$', 'apparelrow.profile.views.settings_publisher', name='settings-publisher'),
    url(r'^settings/description/$', 'apparelrow.profile.views.save_description', name='settings-save-description'),
    url(r'^confirm/email/$', 'apparelrow.profile.views.confirm_email', name='user-confirm-email'),
    url(r'^welcome/$', 'apparelrow.profile.views.login_flow_brands', name='login-flow-brands'),
    url(r'^welcome/complete/$', 'apparelrow.profile.views.login_flow_complete', name='login-flow-complete'),
    url(r'^(?:([^\/]+?)/)?$', 'apparelrow.profile.views.likes', name='profile-likes'),
    url(r'^(?:([^\/]+?)/)?updates/$', RedirectView.as_view(url=reverse_lazy('profile-likes')), name='redirect-profile-updates'),
    url(r'^(?:([^\/]+?)/)?looks/$', 'apparelrow.profile.views.looks', name='profile-looks'),
    url(r'^(?:([^\/]+?)/)?likedlooks/$', 'apparelrow.profile.views.likedlooks', name='profile-likedlooks'),
    url(r'^(?:([^\/]+?)/)?brandlooks/$', 'apparelrow.profile.views.brandlooks', name='profile-brandlooks'),
    url(r'^(?:([^\/]+?)/)?shops/$', 'apparelrow.profile.views.shops', name='profile-shops'),
    url(r'^(?:([^\/]+?)/)?widgets/$', 'apparelrow.profile.views.widgets', name='profile-widgets'),
    url(r'^(?:([^\/]+?)/)?followers/$', 'apparelrow.profile.views.followers', name='profile-followers'),
    url(r'^(?:([^\/]+?)/)?following/$', 'apparelrow.profile.views.following', name='profile-following'),
    url(r'^login/(?P<user_id>\d+)/$', 'apparelrow.profile.views.login_as_user', name='login-as-user'),
)

