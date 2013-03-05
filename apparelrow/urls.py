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
    url(r'^accounts/register/$', 'profile.views.register', name='auth_register'),
    url(r'^accounts/reset/$', 'django.contrib.auth.views.password_reset', name='auth_password_reset'),
    url(r'^accounts/', include('django.contrib.auth.urls')),

    (r'^profile/', include('profile.urls')),

    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^i18n/setlang/$', 'apparel.views.apparel_set_language'), # override builtin set_language
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^admin/', include(admin.site.urls)),
    (r'^newsletter/', include('newsletter.urls')),
    (r'', include('apparel.urls')),
    (r'^partner/', include('dashboard.urls')),
    (r'^s/', include('statistics.urls')),
    url(r'^facebook/login', 'profile.views.login', name='facebook_login'),
    url(r'^facebook/connect', 'profile.views.facebook_connect', name='facebook_connect'),
    url(r'^sitemap\.xml', include('static_sitemaps.urls')),
    url(r'^sitemap-(?P<section>.+)\.xml\.gz$', 'apparel.views.sitemap_view'),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += patterns('django.contrib.flatpages.views',
    url(r'^(?P<url>about/.*)$', 'flatpage', name='about'),
)
