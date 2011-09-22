from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url('^$', 'beta.views.unlock', name='beta_unlock'),
    url('^invite/$', 'beta.views.invite', name='beta_invite'),
    url('^about/$', 'beta.views.about', name='beta_about'),
    url('^requestinvite/$', 'beta.views.request_invite', name='beta_request_invite'),
)
