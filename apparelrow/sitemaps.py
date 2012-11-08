from django.core.urlresolvers import reverse
from django.contrib.sitemaps import Sitemap, FlatPageSitemap, GenericSitemap

from apparel.models import Product, Look
from profile.models import ApparelProfile

class LimitGenericSitemap(GenericSitemap):
    limit = 250

class ViewSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.5

    def items(self):
        return ['brand-list-men', 'brand-list-women', 'brand-list-popular-men', 'brand-list-popular-women',
                'look-list-men', 'look-list-women', 'popular-look-list', 'shop-men', 'shop-women',
                'user-list-men', 'user-list-women', 'user-list-popular-men', 'user-list-popular-women']

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


sitemaps = {
    'flatpages': FlatPageSitemap,
    'product': LimitGenericSitemap({'queryset': Product.published_objects.all(), 'date_field': 'modified'}, priority=0.5),
    'look': LimitGenericSitemap({'queryset': Look.objects.all(), 'date_field': 'modified'}, priority=0.5),
    'user': UserSitemap,
    'views': ViewSitemap,
}
