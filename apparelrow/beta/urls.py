from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url('^$', 'beta.views.unlock', name='beta_unlock'),
    url('^about/$', 'beta.views.about', name='beta_about'),
)
