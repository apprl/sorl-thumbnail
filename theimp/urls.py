from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'theimp.views.index', name='importer-index'),
    url(r'^brand/$', 'theimp.views.brand_mapper', name='brand-mapper'),
    url(r'^category/$', 'theimp.views.category_mapper', name='category-mapper'),
    url(r'^messages/$', 'theimp.views.messages', name='importer-messages'),
)
