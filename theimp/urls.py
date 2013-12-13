from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'theimp.views.index', name='importer-index'),
)
