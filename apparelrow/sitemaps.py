from django.core.urlresolvers import reverse
from django.contrib.sitemaps import Sitemap, FlatPageSitemap, GenericSitemap
from django.db.models import get_model

class LimitGenericSitemap(GenericSitemap):
    limit = 500

class ViewSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.5

    def items(self):
        return ['brand-list-men', 'brand-list-women', 'look-list-men', 'look-list-women',
                'popular-look-list', 'shop-men', 'shop-women', 'user-list-men',
                'user-list-women', 'user-list-popular-men', 'user-list-popular-women']

    def location(self, item):
        return reverse(item)

product_info = {'queryset': get_model('apparel', 'Product').published_objects.order_by('-modified'), 'date_field': 'modified'}
look_info = {'queryset': get_model('apparel', 'Look').published_objects.order_by('-modified'), 'date_field': 'modified'}
profile_info = {'queryset': get_model('profile', 'ApparelProfile').objects.filter(user__is_active=True)}

sitemaps = {
    'flatpages': FlatPageSitemap,
    'views': ViewSitemap,
    'product': LimitGenericSitemap(product_info, priority=0.7, changefreq='daily'),
    'look': LimitGenericSitemap(look_info, priority=0.8, changefreq='daily'),
    'user': LimitGenericSitemap(profile_info, priority=0.6, changefreq='daily'),
}
