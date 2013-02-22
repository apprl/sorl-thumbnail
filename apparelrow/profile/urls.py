from django.conf.urls import patterns, url

urlpatterns = patterns('',
    (r'^settings/$', 'profile.views.settings_notification'),
    (r'^settings/notification/$', 'profile.views.settings_notification'),
    (r'^settings/email/$', 'profile.views.settings_email'),
    (r'^settings/facebook/$', 'profile.views.settings_facebook'),
    (r'^settings/partner/$', 'profile.views.settings_partner'),
    (r'^settings/password/$', 'profile.views.settings_password'),
    (r'^confirm/email/$', 'profile.views.confirm_email'),
    url(r'^welcome/bio/$', 'profile.views.login_flow_bio', name='login-flow-bio'),
    url(r'^welcome/friends/$', 'profile.views.login_flow_friends', name='login-flow-friends'),
    url(r'^welcome/featured/$', 'profile.views.login_flow_featured', name='login-flow-featured'),
    url(r'^welcome/brands/$', 'profile.views.login_flow_brands', name='login-flow-brands'),
    url(r'^welcome/like/$', 'profile.views.login_flow_like', name='login-flow-like'),
    url(r'^welcome/complete/$', 'profile.views.login_flow_complete', name='login-flow-complete'),
    url(r'^(?:([^\/]+?)/)?$', 'profile.views.likes', name='profile-likes'),
    url(r'^(?:([^\/]+?)/)?updates/$', 'profile.views.profile', name='profile-updates'),
    url(r'^(?:([^\/]+?)/)?looks/$', 'profile.views.looks', name='profile-looks'),
    url(r'^(?:([^\/]+?)/)?followers/$', 'profile.views.followers', name='profile-followers'),
    url(r'^(?:([^\/]+?)/)?following/$', 'profile.views.following', name='profile-following'),
)

