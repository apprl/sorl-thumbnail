from django.conf.urls.defaults import patterns, url
from django.views.generic import RedirectView

urlpatterns = patterns('',
    url(r'', RedirectView.as_view(url='http://apprl.us4.list-manage.com/subscribe?u=288a115f8369a96ef3fcf6e9d&id=6fa805a815', permanent=False, query_string=True), name='newsletter-redirect'),
    url(r'^add/$', 'newsletter.views.newsletter_add', name='newsletter-add'),
)

