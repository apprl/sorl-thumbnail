from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'apparelrow.dashboard.views.index', name='index-publisher'),
    url(r'^apply/$', 'apparelrow.dashboard.views.publisher_contact', name='publisher-contact'),
    url(r'^dashboard/$', 'apparelrow.dashboard.views.dashboard', name='dashboard'),
    url(r'^referral/$', 'apparelrow.dashboard.views.referral', name='dashboard-referral'),
    url(r'^complete/$', 'apparelrow.dashboard.views.index_complete', {'view': 'dashboard'}, name='index-dashboard-complete'),
    url(r'^info/$', 'apparelrow.dashboard.views.dashboard_info', name='dashboard-info'),
    url(r'^dashboard/(?P<year>\d{4})/(?P<month>\d{1,2})/', 'apparelrow.dashboard.views.dashboard', name='dashboard-date'),
    url(r'^stores/$', 'apparelrow.dashboard.views.commissions', name='dashboard-commissions'),
    url(r'^stores/(?P<pk>[\d]+)/$', 'apparelrow.dashboard.views.commissions_popup', name='dashboard-commissions-popup'),

    url(r'^referral/mail/$', 'apparelrow.dashboard.views.referral_mail', name='dashboard-referral-mail'),
    url(r'group/(?P<pk>\d+)/$', 'apparelrow.dashboard.views.dashboard_group_admin', name='dashboard-group'),

    url(r'admin/$', 'apparelrow.dashboard.views.dashboard_admin', name='dashboard-admin'),
    url(r'admin/(?P<year>\d{4})/(?P<month>\d{1,2})/$', 'apparelrow.dashboard.views.dashboard_admin', name='dashboard-admin-date'),
)
