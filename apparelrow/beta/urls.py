from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url('^$', 'beta.views.unlock', name='beta_unlock')
)
