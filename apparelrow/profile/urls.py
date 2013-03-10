from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^flow/$', 'apparelrow.profile.views.flow', name='login-flow-redirect'),
    (r'^settings/$', 'apparelrow.profile.views.settings_notification'),
    (r'^settings/notification/$', 'apparelrow.profile.views.settings_notification'),
    (r'^settings/email/$', 'apparelrow.profile.views.settings_email'),
    (r'^settings/facebook/$', 'apparelrow.profile.views.settings_facebook'),
    (r'^settings/partner/$', 'apparelrow.profile.views.settings_partner'),
    (r'^settings/password/$', 'apparelrow.profile.views.settings_password'),
    (r'^confirm/email/$', 'apparelrow.profile.views.confirm_email'),
    url(r'^welcome/friends/$', 'apparelrow.profile.views.login_flow_friends', name='login-flow-friends'),
    url(r'^welcome/featured/$', 'apparelrow.profile.views.login_flow_featured', name='login-flow-featured'),
    url(r'^welcome/brands/$', 'apparelrow.profile.views.login_flow_brands', name='login-flow-brands'),
    url(r'^welcome/complete/$', 'apparelrow.profile.views.login_flow_complete', name='login-flow-complete'),
    url(r'^(?:([^\/]+?)/)?$', 'apparelrow.profile.views.likes', name='profile-likes'),
    url(r'^(?:([^\/]+?)/)?updates/$', 'apparelrow.profile.views.profile', name='profile-updates'),
    url(r'^(?:([^\/]+?)/)?looks/$', 'apparelrow.profile.views.looks', name='profile-looks'),
    url(r'^(?:([^\/]+?)/)?followers/$', 'apparelrow.profile.views.followers', name='profile-followers'),
    url(r'^(?:([^\/]+?)/)?following/$', 'apparelrow.profile.views.following', name='profile-following'),
)

