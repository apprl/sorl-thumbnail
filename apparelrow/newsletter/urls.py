from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^add/$', 'newsletter.views.newsletter_add', name='newsletter-add'),
)

