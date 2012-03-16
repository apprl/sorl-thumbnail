from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    (r'^settings/$', 'profile.views.settings_notification'),
    (r'^settings/notification/$', 'profile.views.settings_notification'),
    (r'^settings/email/$', 'profile.views.settings_email'),
    (r'^confirm/email/$', 'profile.views.confirm_email'),
    (r'^welcome/$', 'profile.views.welcome_dialog'),
    url(r'^(?:([^\/]+?)/)?$', 'apparel.browse.browse_profile', name='profile-likes'),
    url(r'^(?:([^\/]+?)/)?updates/$', 'profile.views.profile', name='profile-updates'),
    url(r'^(?:([^\/]+?)/)?looks/$', 'profile.views.looks', name='profile-looks'),
    url(r'^(?:([^\/]+?)/)?followers/$', 'profile.views.followers', name='profile-followers'),
    url(r'^(?:([^\/]+?)/)?following/$', 'profile.views.following', name='profile-following'),
)

