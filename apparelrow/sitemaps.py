from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib.sitemaps import Sitemap, FlatPageSitemap, GenericSitemap
from django.db.models import get_model

from localeurl.templatetags.localeurl_tags import chlocale


class LimitGenericSitemap(GenericSitemap):
    limit = 2000

    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop('language')
        super(LimitGenericSitemap, self).__init__(*args, **kwargs)

    def location(self, item):
        return chlocale(item.get_absolute_url(), self.language)


class ViewSitemap(Sitemap):
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


class LocaleFlatPageSitemap(FlatPageSitemap):
    def __init__(self, language):
        self.language = language

    def location(self, item):
        return chlocale(item.get_absolute_url(), self.language)


product_info = {'queryset': get_model('apparel', 'Product').published_objects.order_by('-popularity')[:1000]}
look_info = {'queryset': get_model('apparel', 'Look').published_objects.order_by('pk')}
profile_info = {'queryset': get_user_model().objects.filter(is_active=True, is_brand=False)}
brand_info = {'queryset': get_user_model().objects.filter(is_active=True, is_brand=True).order_by('-followers_count')[:100]}


sitemaps = {
    'flatpages-sv': LocaleFlatPageSitemap(language='sv'),
    'flatpages-en': LocaleFlatPageSitemap(language='en'),
    'views-sv': ViewSitemap(language='sv'),
    'views-en': ViewSitemap(language='en'),
    'product-sv': LimitGenericSitemap(product_info, priority=0.6, changefreq='daily', language='sv'),
    'product-en': LimitGenericSitemap(product_info, priority=0.6, changefreq='daily', language='en'),
    'look-sv': LimitGenericSitemap(look_info, priority=0.9, changefreq='daily', language='sv'),
    'look-en': LimitGenericSitemap(look_info, priority=0.9, changefreq='daily', language='en'),
    'user-sv': LimitGenericSitemap(profile_info, priority=0.7, changefreq='daily', language='sv'),
    'user-en': LimitGenericSitemap(profile_info, priority=0.7, changefreq='daily', language='en'),
    'brand-sv': LimitGenericSitemap(brand_info, priority=0.7, changefreq='daily', language='sv'),
    'brand-en': LimitGenericSitemap(brand_info, priority=0.7, changefreq='daily', language='en'),
}
