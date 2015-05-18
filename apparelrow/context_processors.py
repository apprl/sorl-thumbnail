from django.conf import settings as django_settings
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db.models import get_model
from django.utils.translation import get_language

def exposed_settings(request):
    current_site = Site.objects.get_current()
    return {
        'CACHE_TIMEOUT': django_settings.CACHES.get('default', {}).get('TIMEOUT', 60),
        'GOOGLE_ANALYTICS_ACCOUNT': django_settings.GOOGLE_ANALYTICS_ACCOUNT,
        'GOOGLE_ANALYTICS_DOMAIN': django_settings.GOOGLE_ANALYTICS_DOMAIN,
        'GOOGLE_ANALYTICS_UNIVERSAL_ACCOUNT': django_settings.GOOGLE_ANALYTICS_UNIVERSAL_ACCOUNT,
        'GOOGLE_ANALYTICS_UNIVERSAL_DOMAIN': django_settings.GOOGLE_ANALYTICS_UNIVERSAL_DOMAIN,
        'GOOGLE_TAG_MANAGER_CONTAINER_ID': django_settings.GOOGLE_TAG_MANAGER_CONTAINER_ID,
        'LANGUAGES_DISPLAY': django_settings.LANGUAGES_DISPLAY,
        'SHORT_LANGUAGES_DISPLAY': django_settings.SHORT_LANGUAGES_DISPLAY,
        'SHORT_LANGUAGES_LIST_DISPLAY': django_settings.SHORT_LANGUAGES_LIST_DISPLAY,
        'LOCATION_LANGUAGE_MAPPING': django_settings.LOCATION_LANGUAGE_MAPPING,
        'CURRENT_DOMAIN': current_site.domain,
        'CURRENT_NAME': current_site.name,
        'FACEBOOK_APP_ID': django_settings.FACEBOOK_APP_ID,
        'FACEBOOK_SCOPE': django_settings.FACEBOOK_SCOPE,
        'FACEBOOK_OG_TYPE': django_settings.FACEBOOK_OG_TYPE,
        'FACEBOOK_REDIRECT_URI': request.build_absolute_uri(reverse('auth_facebook_login')),
        'CURRENCY': django_settings.LANGUAGE_TO_CURRENCY.get(get_language(), django_settings.APPAREL_BASE_CURRENCY),
        'STATIC_URL': django_settings.STATIC_URL,
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

def currency(request):
    rates = cache.get(django_settings.APPAREL_RATES_CACHE_KEY)
    if not rates:
        fxrate_model = get_model('importer', 'FXRate')
        rates = {}
        for rate_obj in fxrate_model.objects.filter(base_currency=django_settings.APPAREL_BASE_CURRENCY):#.values('currency', 'rate'):
            rates[rate_obj.currency] = rate_obj.rate

        if rates:
            cache.set(django_settings.APPAREL_RATES_CACHE_KEY, rates, 60*60)

    return {'currency_rates': rates}
