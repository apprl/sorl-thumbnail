from django.conf.urls import *
from apparel.models import *
from watcher.views import *

urlpatterns = patterns('',
    (r'^save/(?P<query>.+)$', save_query),
    (r'^(?P<name>.+?)(?:/(?P<format>.+))?$', execute),
)
