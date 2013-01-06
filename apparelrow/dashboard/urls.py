from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'dashboard.views.dashboard', name='dashboard'),
    url(r'^complete/$', 'dashboard.views.dashboard_complete', name='dashboard-complete'),
    url(r'^info/$', 'dashboard.views.dashboard_info', name='dashboard-info'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/', 'dashboard.views.dashboard', name='dashboard-date'),
)
