from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^settings/$', 'profile.views.settings_notification'),
    (r'^settings/notification/$', 'profile.views.settings_notification'),
    (r'^settings/email/$', 'profile.views.settings_email'),
    (r'^confirm/email/$', 'profile.views.confirm_email'),
    (r'^welcome/$', 'profile.views.welcome_dialog'),
    (r'^(?:([^\/]+?)/)?$', 'profile.views.profile'),
    (r'^(?:([^\/]+?)/)?looks/$', 'profile.views.looks'),
    (r'^(?:([^\/]+?)/)?likes/$', 'apparel.browse.browse_profile'),
    (r'^(?:([^\/]+?)/)?followers/$', 'profile.views.followers'),
    (r'^(?:([^\/]+?)/)?following/$', 'profile.views.following'),
)

