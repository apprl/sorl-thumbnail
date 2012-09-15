from django.conf import settings as django_settings
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

from apparel.utils import get_gender_from_cookie

def exposed_settings(request):
    current_site = Site.objects.get_current()
    return {
        'CACHE_LONG_TIMEOUT': 60 * 60 * 12,
        'CACHE_TIMEOUT': django_settings.CACHES.get('default', {}).get('TIMEOUT', 60),
        'DEFAULT_AVATAR': django_settings.APPAREL_DEFAULT_AVATAR,
        'DEFAULT_AVATAR_LARGE': django_settings.APPAREL_DEFAULT_AVATAR_LARGE,
        'GOOGLE_ANALYTICS_ACCOUNT': django_settings.GOOGLE_ANALYTICS_ACCOUNT,
        'GOOGLE_ANALYTICS_DOMAIN': django_settings.GOOGLE_ANALYTICS_DOMAIN,
        'SHORT_LANGUAGES': django_settings.SHORT_LANGUAGES,
        'CURRENT_DOMAIN': current_site.domain,
        'CURRENT_NAME': current_site.name,
        'FACEBOOK_APP_ID': django_settings.FACEBOOK_APP_ID,
        'FACEBOOK_SCOPE': django_settings.FACEBOOK_SCOPE,
        'FACEBOOK_OG_TYPE': django_settings.FACEBOOK_OG_TYPE
    }

def next_redirects(request):
    if reverse('django.contrib.auth.views.logout') == request.path:
        return {
            'next' : '/'
        }
    else:
        return {
            'next' : request.path
        }

def gender(request):
    return {'APPAREL_GENDER': get_gender_from_cookie(request)}
