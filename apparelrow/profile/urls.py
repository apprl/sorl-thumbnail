from django.conf.urls.defaults import *
from apparel.models import *


#wardrobe_dict = {
#    'queryset': Wardrobe.objects.filter(user=request.user),
#}


urlpatterns = patterns('',
    (r'^$', 'django.views.generic.simple.direct_to_template', {'template': 'profile/profile.html'}),
    (r'^watcher/$', 'watcher.views.manage'),
 #   (r'^wardrobe/$', 'django.views.generic.list_detail.object_list', wardrobe_dict),
)

