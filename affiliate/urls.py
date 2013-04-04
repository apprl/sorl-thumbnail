from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^conversion/$', 'affiliate.views.pixel', name='affiliate-pixel'),
    url(r'^link/$', 'affiliate.views.link', name='affiliate-link'),
    url(r'^admin/$', 'affiliate.views.store_admin', name='affiliate-store-admin'),
    url(r'^admin/(?P<year>\d{4})/(?P<month>\d{1,2})/$', 'affiliate.views.store_admin', name='affiliate-store-admin-date'),
    url(r'^admin/(?P<transaction_id>[\d]+)/accept/$', 'affiliate.views.store_admin_accept', name='affiliate-admin-accept'),
    url(r'^admin/(?P<transaction_id>[\d]+)/reject/$', 'affiliate.views.store_admin_reject', name='affiliate-admin-reject'),
)
