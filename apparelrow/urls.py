from django.conf import settings
from django.conf.urls import patterns, url, include, handler404, handler500
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib import admin
admin.autodiscover()

#from account.openid_consumer import PinaxConsumer

#if settings.ACCOUNT_OPEN_SIGNUP:
#    signup_view = "account.views.signup"
#else:
#    signup_view = "signup_codes.views.signup"

from sitemaps import sitemaps


urlpatterns = patterns('',
#    url(r'^admin/invite_user/$', 'signup_codes.views.admin_invite_user', name="admin_invite_user"),
#    url(r'^account/signup/$', signup_view, name="acct_signup"),

    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', { 'domain': 'djangojs', 'packages': ('apparelrow',),}),

    url(r'^accounts/login/$', auth_views.login, {'template_name': 'registration/login.html'}, name='auth_login'),
    url(r'^accounts/logout/$', auth_views.logout, {'template_name': 'registration/logout.html'}, name='auth_logout'),
    url(r'^accounts/register/$', 'profile.views.register', name='auth_register'),
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
    url(r'^sitemap\.xml', include('static_sitemaps.urls')),
    url(r'^sitemap-(?P<section>.+)\.xml\.gz$', 'apparel.views.sitemap_view'),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += patterns('django.contrib.flatpages.views',
    url(r'^(?P<url>about/.*)$', 'flatpage', name='about'),
)
