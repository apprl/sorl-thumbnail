from django.conf.urls.defaults import *
from apparel.models import *



urlpatterns = patterns('',
    (r'^$', 'profile.views.home'),
    (r'^(?:([^\/]+?)/)?$', 'profile.views.profile'),
    (r'^(?:([^\/]+?)/)?looks/$', 'profile.views.looks'),
 #   url(r'^(?P<profile>.*)/looks$', view='apparel.views.look_list', name='looks_by_user'),
 #    (r'^watcher/$', 'watcher.views.manage'),
    (r'^(?:([^\/]+?)/)?wardrobe/$', 'apparel.views.wardrobe'),
    (r'^(?:([^\/]+?)/)?followers/$', 'profile.views.followers'),
    (r'^(?:([^\/]+?)/)?following/$', 'profile.views.following'),
)

