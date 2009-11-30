from django.conf.urls.defaults import *
from apparel.models import *
from django.db.models import Q


urlpatterns = patterns('',
    (r'^$', 'django.views.generic.simple.direct_to_template', {'template': 'profile/profile.html'}),
    (r'^watch$', 'watch.views.manage'),
)

