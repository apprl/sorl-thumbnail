from django.conf import settings
from django.conf.urls import patterns, url, include, handler404, handler500
from django.conf.urls.static import static
from django.contrib import admin
admin.autodiscover()

from sitemaps import sitemaps

urlpatterns = patterns('',
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', { 'domain': 'djangojs', 'packages': ('apparelrow',),}),

    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'registration/login.html'}, name='auth_login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': '/accounts/register/'}, name='auth_logout'),
    url(r'^accounts/register/$', 'apparelrow.profile.views.register', name='auth_register'),
    url(r'^accounts/register/email/$', 'apparelrow.profile.views.register_email', name='auth_register_email'),
    url(r'^accounts/register/complete/$', 'apparelrow.profile.views.register_complete', name='auth_register_complete'),
    url(r'^accounts/activate/(?P<key>[\w-]+)/$', 'apparelrow.profile.views.register_activate', name='auth_register_activate'),
    url(r'^accounts/reset/$', 'django.contrib.auth.views.password_reset', name='auth_password_reset'),
    url(r'^accounts/', include('django.contrib.auth.urls')),

    (r'^profile/', include('apparelrow.profile.urls')),

    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^i18n/setlang/$', 'apparelrow.apparel.views.apparel_set_language'), # override builtin set_language
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^admin/', include(admin.site.urls)),
    (r'^newsletter/', include('apparelrow.newsletter.urls')),
    (r'', include('apparelrow.apparel.urls')),
    (r'^partner/', include('apparelrow.dashboard.urls')),
    (r'^s/', include('apparelrow.statistics.urls')),
    url(r'^facebook/login', 'apparelrow.profile.views.facebook_login', name='facebook_login'),
    url(r'^facebook/connect', 'apparelrow.profile.views.facebook_connect', name='facebook_connect'),
    url(r'^sitemap\.xml', include('static_sitemaps.urls')),
    url(r'^sitemap-(?P<section>.+)\.xml\.gz$', 'apparelrow.apparel.views.sitemap_view'),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += patterns('django.contrib.flatpages.views',
    url(r'^(?P<url>about/.*)$', 'flatpage', name='about'),
)
