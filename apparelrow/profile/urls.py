from django.conf.urls.defaults import *
from apparel.models import *



urlpatterns = patterns('',
    (r'^(?:([^\/]+?)/)?$', 'profile.views.profile'),
    (r'^(?:([^\/]+?)/)?looks/$', 'profile.views.looks'),
 #   url(r'^(?P<profile>.*)/looks$', view='apparel.views.look_list', name='looks_by_user'),
 #    (r'^watcher/$', 'watcher.views.manage'),
    (r'^(?:([^\/]+?)/)?wardrobe/$', 'django.views.generic.simple.direct_to_template', {'template': 'profile/wardrobe.html'}),
)

