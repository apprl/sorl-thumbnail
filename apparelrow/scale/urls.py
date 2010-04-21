from django.conf.urls.defaults import *


urlpatterns = patterns('',
    # FIXME: Replace site_media/media with whatever prefix is used in the system
    (r'^(?P<size>\d+(?:x\d+)?)/?(?:media/)?(?P<path>.+)$', 'scale.views.thumb'),
)
