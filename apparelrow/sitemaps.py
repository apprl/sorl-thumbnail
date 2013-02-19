from django.core.urlresolvers import reverse
from django.contrib.sitemaps import Sitemap, FlatPageSitemap, GenericSitemap

from apparel.models import Product, Look
from profile.models import ApparelProfile

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

class UserSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.5

    def items(self):
        return ApparelProfile.objects.filter(user__is_active=True)

    def location(self, item):
        return reverse('profile-likes', args=[item.slug])
        #return [
            #reverse('profile-likes', args=[item.slug]),
            #reverse('profile-updates', args=[item.slug]),
            #reverse('profile-looks', args=[item.slug]),
            #reverse('profile-followers', args=[item.slug]),
            #reverse('profile-following', args=[item.slug]),
        #]


product_info = {'queryset': Product.published_objects.order_by('-modified'), 'date_field': 'modified'}
look_info = {'queryset': Look.published_objects.order_by('-modified'), 'date_field': 'modified'}
profile_info = {'queryset': ApparelProfile.objects.filter(user__is_active=True)}

sitemaps = {
    'flatpages': FlatPageSitemap,
    'views': ViewSitemap,
    'product': LimitGenericSitemap(product_info, priority=0.7, changefreq='daily'),
    'look': LimitGenericSitemap(look_info, priority=0.8, changefreq='daily'),
    'user': LimitGenericSitemap(profile_info, priority=0.6, changefreq='daily'),
}
