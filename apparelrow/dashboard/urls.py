from django.conf.urls import patterns, url
from apparelrow.dashboard.views import DashboardView, AdminDashboardView, PublisherToolsView, ReferralView
from django.views.generic import RedirectView

urlpatterns = patterns('',
    url(r'^$', RedirectView.as_view(url='/', permanent=False), name='index-publisher'),
    url(r'^apply/$', 'apparelrow.dashboard.views.publisher_contact', name='publisher-contact'),
    url(r'^referral/$', ReferralView.as_view(), name='dashboard-referral'),
    url(r'^complete/$', 'apparelrow.dashboard.views.index_complete', {'view': 'dashboard'}, name='index-dashboard-complete'),
    url(r'^info/$', 'apparelrow.dashboard.views.dashboard_info', name='dashboard-info'),
    url(r'^stores/$', 'apparelrow.dashboard.views.commissions', name='dashboard-commissions'),
    url(r'^stores/(?P<pk>[\d]+)/$', 'apparelrow.dashboard.views.commissions_popup', name='dashboard-commissions-popup'),
    url(r'^tools/$', PublisherToolsView.as_view(), name='publisher-tools'),


    url(r'group/(?P<pk>\d+)/$', 'apparelrow.dashboard.views.dashboard_group_admin', name='dashboard-group'),

    url(r'^admin/$', AdminDashboardView.as_view(), name='dashboard-admin'),
    url(r'^admin/(?P<year>\d{4})/(?P<month>\d{1,2})/$', AdminDashboardView.as_view(), name='dashboard-admin-date'),
    url(r'^dashboard/$', DashboardView.as_view(), name='dashboard'),
    url(r'^dashboard/(?P<year>\d{4})/(?P<month>\d{1,2})/$', DashboardView.as_view(), name='dashboard-date'),
)
