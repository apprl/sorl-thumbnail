from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^conversion/$', 'affiliate.views.pixel', name='affiliate-pixel'),
    url(r'^link/$', 'affiliate.views.link', name='affiliate-link'),
    url(r'^admin/$', 'affiliate.views.store_admin', name='affiliate-store-admin'),
)
