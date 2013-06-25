from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^conversion/$', 'advertiser.views.pixel', name='advertiser-pixel'),
    url(r'^link/$', 'advertiser.views.link', name='advertiser-link'),
    url(r'^admin/$', 'advertiser.views.store_admin', name='advertiser-store-admin'),
    url(r'^admin/(?P<year>\d{4})/(?P<month>\d{1,2})/$', 'advertiser.views.store_admin', name='advertiser-store-admin-date'),
    url(r'^admin/(?P<transaction_id>[\d]+)/accept/$', 'advertiser.views.store_admin_accept', name='advertiser-admin-accept'),
    url(r'^admin/(?P<transaction_id>[\d]+)/reject/$', 'advertiser.views.store_admin_reject', name='advertiser-admin-reject'),
    url(r'^admin/test_link/$', 'advertiser.views.test_link', name='advertiser-test-link'),
)
