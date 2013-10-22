from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.contrib.sitemaps import Sitemap, FlatPageSitemap, GenericSitemap
from django.db.models import get_model

from localeurl.templatetags.localeurl_tags import chlocale


class LocaleSitemap(GenericSitemap):

    sitemap_template = 'sitemap.xml'

    def __get(self, name, obj, default=None):
        try:
            attr = getattr(self, name)
        except AttributeError:
            return default
        if callable(attr):
            return attr(obj)
        return attr

    def get_urls(self, page=1, site=None, protocol=None):
        # Determine protocol
        if self.protocol is not None:
            protocol = self.protocol
        if protocol is None:
            protocol = 'http'

        # Determine domain
        if site is None:
            if Site._meta.installed:
                try:
                    site = Site.objects.get_current()
                except Site.DoesNotExist:
                    pass
            if site is None:
                raise ImproperlyConfigured("To use sitemaps, either enable the sites framework or pass a Site/RequestSite object in your view.")
        domain = site.domain

        urls = []
        latest_lastmod = None
        all_items_lastmod = True  # track if all items have a lastmod
        for item in self.paginator.page(page).object_list:
            languages = []
            for language in settings.LANGUAGES_DISPLAY:
                languages.append((language[0], '%s://%s%s' % (protocol, domain, chlocale(self.__get('location', item), language[0]))))
            loc = "%s://%s%s" % (protocol, domain, self.__get('location', item))
            priority = self.__get('priority', item, None)
            lastmod = self.__get('lastmod', item, None)
            if all_items_lastmod:
                all_items_lastmod = lastmod is not None
                if (all_items_lastmod and
                    (latest_lastmod is None or lastmod > latest_lastmod)):
                    latest_lastmod = lastmod
            url_info = {
                'item':       item,
                'location':   loc,
                'lastmod':    lastmod,
                'changefreq': self.__get('changefreq', item, None),
                'priority':   str(priority if priority is not None else ''),
                'languages':  languages,
            }
            urls.append(url_info)
        if all_items_lastmod and latest_lastmod:
            self.latest_lastmod = latest_lastmod
        return urls


class LimitGenericSitemap(LocaleSitemap):

    limit = 2000

    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop('language')
        super(LimitGenericSitemap, self).__init__(*args, **kwargs)

    def location(self, item):
        return chlocale(item.get_absolute_url(), self.language)

class ViewSitemap(GenericSitemap):
    changefreq = 'daily'
    priority = 0.8

    def __init__(self, language):
        self.language = language

    def items(self):
        return ['brand-list-men', 'brand-list-women',
                'look-list-men', 'look-list-women',
                'shop-men', 'shop-women',
                'user-list-men', 'user-list-women']

    def location(self, item):
        return chlocale(reverse(item), self.language)

    def lastmod(self, item):
        return None


class FlatPageSitemap(LocaleSitemap):
    def __init__(self, language):
        self.language = language

    def location(self, item):
        return chlocale(item.get_absolute_url(), self.language)

    def items(self):
        current_site = Site.objects.get_current()
        return current_site.flatpage_set.filter(registration_required=False)

    def lastmod(self, item):
        return None


product_info = {'queryset': get_model('apparel', 'Product').published_objects.order_by('-popularity')[:1000]}
look_info = {'queryset': get_model('apparel', 'Look').published_objects.order_by('pk')}
profile_info = {'queryset': get_user_model().objects.filter(is_active=True, is_brand=False)}
brand_info = {'queryset': get_user_model().objects.filter(is_active=True, is_brand=True).order_by('-followers_count')[:100]}


sitemaps = {
    'flatpages': FlatPageSitemap(language='en'),
    'views': ViewSitemap(language='en'),
    'product': LimitGenericSitemap(product_info, priority=0.6, changefreq='daily', language='en'),
    'look': LimitGenericSitemap(look_info, priority=0.9, changefreq='daily', language='en'),
    'user': LimitGenericSitemap(profile_info, priority=0.7, changefreq='daily', language='en'),
    'brand': LimitGenericSitemap(brand_info, priority=0.7, changefreq='daily', language='en'),
}
