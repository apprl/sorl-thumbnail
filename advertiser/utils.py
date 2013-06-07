import urllib

from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

site_object = Site.objects.get_current()

def make_advertiser_url(store_id, url):
    base_url = 'http://%s%s' % (site_object.domain, reverse('advertiser-link'))

    return '%s?store_id=%s&url=%s' % (base_url, store_id, urllib.quote(url, ''))
