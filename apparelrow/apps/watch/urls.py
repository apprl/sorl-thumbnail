from django.conf.urls.defaults import *
from apparel.models import *
from watch.views import *

urlpatterns = patterns('',
    (r'^(?P<name>.+?)(?:/(?P<format>.+))?$', watch_result),
    (r'^save/(?P<query>\w+)$', save_query),
)

