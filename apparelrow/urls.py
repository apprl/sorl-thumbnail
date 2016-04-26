from django.conf import settings
from django.conf.urls import patterns, url, include, handler404, handler500
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import RedirectView
from apparelrow.profile.views import RegisterEmailFormView, RegisterEmailCompleteFormView, RegisterActivateView, \
    RegisterView

admin.autodiscover()

from apparelrow.profile.forms import EmailValidationResetPassword

from sitemaps import sitemaps

urlpatterns = patterns('',
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', { 'domain': 'djangojs', 'packages': ('apparelrow',),}),

    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'registration/login.html'}, name='auth_login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': '/accounts/login/'}, name='auth_logout'),
    url(r'^accounts/register/$', RegisterView.as_view(), name='auth_register'),
    #url(r'^accounts/register/$', 'apparelrow.profile.views.register', name='auth_register'),
    url(r'^accounts/register/email/$', RegisterEmailFormView.as_view(template_name="registration/registration_email.html"), name='auth_register_email'),
    url(r'^accounts/register/email2/$', RegisterEmailFormView.as_view(template_name="registration/registration_email-2.html"), name='auth_register_email2'),
    #url(r'^accounts/register/email/$', 'apparelrow.profile.views.register_email', name='auth_register_email'),
    url(r'^accounts/register/complete/$', RegisterEmailCompleteFormView.as_view(), name='auth_register_complete'),
    #url(r'^accounts/register/complete/$', 'apparelrow.profile.views.register_complete', name='auth_register_complete'),
    #url(r'^accounts/activate/(?P<key>[\w-]+)/$', 'apparelrow.profile.views.register_activate', name='auth_register_activate'),
    url(r'^accounts/activate/(?P<key>[\w-]+)/$', RegisterActivateView.as_view(), name='auth_register_activate'),
    url(r'^accounts/reset/$', 'django.contrib.auth.views.password_reset', {'password_reset_form': EmailValidationResetPassword}, name='auth_password_reset'),
    url(r'^accounts/facebook/login', 'apparelrow.profile.views.facebook_redirect_login', name='auth_facebook_login'),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^a/', include('advertiser.urls')),

    # Alias for store signup with analytics campaign for Ad
    url(r'^addstore/$', RedirectView.as_view(url='http://apprl.com/en/store?utm_source=AddStore&utm_medium=AddStore&utm_campaign=signupAddStore')),
    url(r'^newsletter/$', RedirectView.as_view(url='http://apprl.us4.list-manage.com/subscribe?u=288a115f8369a96ef3fcf6e9d&id=6fa805a815', permanent=False, query_string=True), name='newsletter-redirect'),

    url(r'^i/(?P<code>[\w-]+)/$', 'apparelrow.dashboard.views.referral_signup', name='dashboard-referral-signup'),

    (r'^profile/', include('apparelrow.profile.urls')),

    (r'^comments/', include('django.contrib.comments.urls')),
    url(r'^i18n/setlang/$', 'apparelrow.apparel.views.apparel_set_language', name='change_language_view'), # override builtin set_language
    (r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^admin/rosetta/', include('rosetta.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'', include('apparelrow.apparel.urls')),
    (r'^partner/', RedirectView.as_view(url='/publisher/dashboard/')),
    (r'^publisher/', include('apparelrow.dashboard.urls')),
    url(r'^facebook/login', 'apparelrow.profile.views.facebook_login', name='facebook_login'),
    url(r'^facebook/connect', 'apparelrow.profile.views.facebook_connect', name='facebook_connect'),
    url(r'^sitemap\.xml', include('static_sitemaps.urls')),
    url(r'^sitemap-(?P<section>.+)\.xml\.gz$', 'apparelrow.apparel.views.sitemap_view'),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += patterns('django.contrib.flatpages.views',
    url(r'^(?P<url>about/.*)$', 'flatpage', name='about'),

    # Temporary url for new home page (work in progress)
    url(r'^home/$', 'flatpage', name='home'),

    # Temporary url for onboarding page (work in progress)
    url(r'^onboarding/$', 'flatpage', name='onboarding'),
)
