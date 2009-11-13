from django.conf.urls.defaults import *
from django.conf import settings

from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

#from account.openid_consumer import PinaxConsumer


#if settings.ACCOUNT_OPEN_SIGNUP:
#    signup_view = "account.views.signup"
#else:
#    signup_view = "signup_codes.views.signup"

urlpatterns = patterns('',
    url(r'^$', direct_to_template, {
        "template": "homepage.html",
    }, name="home"),

#    url(r'^admin/invite_user/$', 'signup_codes.views.admin_invite_user', name="admin_invite_user"),
#    url(r'^account/signup/$', signup_view, name="acct_signup"),
    
    (r'^about/', include('about.urls')),
    
    # FIXME: Is it possible to include this in some other way? All I want to do
    # is to pass the next_page attribute (and not do it via query)
    (r'^accounts/', include('registration.backends.default.urls')),
    (r'^facebookconnect/', include('facebookconnect.urls')),    

#    (r'^account/login/$', 'django.contrib.auth.views.login'),
#    (r'^account/logout/$', 'django.contrib.auth.views.logout'),

#    (r'^account/', include('account.urls')),
#    (r'^profiles/', include('basic_profiles.urls')),
    (r'^notices/', include('notification.urls')),
    (r'^announcements/', include('announcements.urls')),
    (r'^apparel/', include('apparel.urls')),
    (r'^scale/', include('scale.urls')),
    (r'^admin/(.*)', admin.site.root),
    (r'^site_media/media/static/(?P<path>.*)$', 'django.views.static.serve', { 'document_root': settings.STATIC_ROOT + '/../site_media/media/static' } ),
    (r'^site_media/static/(?P<path>.*)$', 'django.views.static.serve', { 'document_root': settings.STATIC_ROOT } ),
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', { 'document_root': settings.STATIC_ROOT } ),
)


