from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'dashboard.views.dashboard', name='dashboard'),
    url(r'^complete/$', 'dashboard.views.dashboard_complete', name='dashboard-complete'),
    url(r'^info/$', 'dashboard.views.dashboard_info', name='dashboard-info'),
    url(r'^info/more/$', 'dashboard.views.dashboard_more_info', name='dashboard-more-info'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/', 'dashboard.views.dashboard', name='dashboard-date'),

    url(r'admin/$', 'dashboard.views.dashboard_admin', name='dashboard-admin'),
    url(r'admin/(?P<year>\d{4})/(?P<month>\d{1,2})/$', 'dashboard.views.dashboard_admin', name='dashboard-admin-date'),
)
