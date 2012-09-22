from django.conf.urls import *

urlpatterns = patterns('',
    (r'^decorator/auth/$', 'apparel.tests.decorators.view_func_auth'),
    (r'^decorator/(?P<rval>.+?)/$', 'apparel.tests.decorators.view_func'),
    (r'^ping/', include('trackback.urls')),
)

