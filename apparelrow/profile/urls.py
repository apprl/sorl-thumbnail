from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^settings/$', 'profile.views.settings_notification'),
    (r'^settings/notification/$', 'profile.views.settings_notification'),
    (r'^settings/email/$', 'profile.views.settings_email'),
    (r'^confirm/email/$', 'profile.views.confirm_email'),
    (r'^(?:([^\/]+?)/)?$', 'profile.views.profile'),
    (r'^(?:([^\/]+?)/)?looks/$', 'profile.views.looks'),
    (r'^(?:([^\/]+?)/)?wardrobe/$', 'apparel.browse.browse_wardrobe'),
    (r'^(?:([^\/]+?)/)?followers/$', 'profile.views.followers'),
    (r'^(?:([^\/]+?)/)?following/$', 'profile.views.following'),
)

