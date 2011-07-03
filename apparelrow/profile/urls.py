from django.conf.urls.defaults import *
from apparel.models import *



urlpatterns = patterns('',
    (r'^(?:([^\/]+?)/)?$', 'profile.views.profile'),
    (r'^(?:([^\/]+?)/)?looks/$', 'profile.views.looks'),
 #   url(r'^(?P<profile>.*)/looks$', view='apparel.views.look_list', name='looks_by_user'),
 #    (r'^watcher/$', 'watcher.views.manage'),
    (r'^(?:([^\/]+?)/)?wardrobe/$', 'apparel.browse.browse_wardrobe'),
    (r'^(?:([^\/]+?)/)?followers/$', 'profile.views.followers'),
    (r'^(?:([^\/]+?)/)?following/$', 'profile.views.following'),
)

